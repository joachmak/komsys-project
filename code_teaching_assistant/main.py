from typing import Optional
from threading import Thread
import os.path
from playsound import playsound

from appJar import gui
from enum import Enum
from uuid import uuid1

from stmpy import Machine, Driver

from code_teaching_assistant.stm_utils import get_stm_transitions, get_stm_states
from common.feedback import Feedback
from common.group import Group
from common.io_utils import import_modules, import_groups
from common.help_request import HelpRequest, RequestStatus
from common.mqtt_utils import parse_help_request, get_request_type, parse_cancel_request, parse_feedback, TOPIC_TASK, \
    BROKER, PORT, TOPIC_QUEUE, RequestWrapper, TYPE_CLAIM_REQUEST, TYPE_ADD_HELP_REQUEST, TYPE_CANCEL_HELP_REQUEST, \
    TYPE_SEND_FEEDBACK, TYPE_CONFIRM_CLAIM, TYPE_RESOLVE_REQUEST, TYPE_CANCEL_CLAIM, \
    parse_body_field
import paho.mqtt.client as mqtt


class MQTTClient:
    def __init__(self, stm_teaching_assistant, help_requests:list):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.stm_teaching_assistant = stm_teaching_assistant
        self.help_requests = help_requests
        self.help_request_to_add = None
        self.help_request_to_remove = None
        self.incoming_feedback = []
        self.logged_in_ta = None
       
        print(f"Trying to connect to {BROKER}")
        self.client.connect(BROKER, PORT)
        self.client.subscribe(TOPIC_QUEUE)
        self.client.subscribe(TOPIC_TASK)
        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        print(format(mqtt.connack_string(rc)))

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        print("on_message(): topic: {}, data: {}".format(msg.topic, msg.payload))
        payload = str(msg.payload).replace("\\", "")
        req_type = get_request_type(str(msg.payload).replace("\\", ""))
        if req_type == TYPE_ADD_HELP_REQUEST:
            self.help_request_to_add = parse_help_request(payload)
            self.stm_teaching_assistant.send("sig_rec_help_req")
            # Make sound to notify the TA's
            file_path = os.path.join("data", "notification_sound.wav")
            playsound(file_path)
        elif req_type == TYPE_CANCEL_HELP_REQUEST:
            self.help_request_to_remove = parse_cancel_request(payload)
            self.stm_teaching_assistant.send("sig_rem_help_req")
        elif req_type == TYPE_SEND_FEEDBACK:
            self.incoming_feedback.append(parse_feedback(payload))
            self.stm_teaching_assistant.send("sig_feedback")
        elif req_type == TYPE_CONFIRM_CLAIM:
            print("Received claim confirmation")
            ta = parse_body_field(payload, "ta")
            if ta == self.logged_in_ta:
                print("ta name matches")
                self.stm_teaching_assistant.send("sig_acc_claim")

    def claim_request(self, request: HelpRequest, ta_name: str) -> bool:
        print(f"going to claim request {request.id}")
        req_body = RequestWrapper(TYPE_CLAIM_REQUEST, str({'id': request.id, 'ta': ta_name})).payload()
        return self.client.publish(TOPIC_QUEUE, payload=req_body).is_published()

    def resolve_request(self, req_id: str):
        req_body = RequestWrapper(TYPE_RESOLVE_REQUEST, str({'id': req_id})).payload()
        return self.client.publish(TOPIC_QUEUE, payload=req_body).is_published()

    def cancel_claim(self, req_id: str):
        req_body = RequestWrapper(TYPE_CANCEL_CLAIM, str({'id': req_id})).payload()
        return self.client.publish(TOPIC_QUEUE, payload=req_body).is_published()


class Scene(Enum):
    LOGIN: int = 0
    MAIN_PAGE: int = 1
    HELP_REQUEST: int = 2
    MARK_TASK_AS_DONE: int = 3
    TASK_MENU: int = 4


class UserInterface:
    def __init__(self, modules: list, groups: list):
        self.app = gui("Teacher Assistant Client", "1x1")  # size is set in show_scene() method
        self.help_requests = []
        self.stm_teaching_assistant = Machine(name="stm_teaching_assistant", transitions=get_stm_transitions(), obj=self, states=get_stm_states())
        self.driver = Driver()
        self.driver.add_machine(self.stm_teaching_assistant)
        self.driver.start()

        self.mqtt_client = MQTTClient(self.stm_teaching_assistant, self.help_requests)

        self.current_scene = -1
        self.modules = modules
        self.groups = groups
        self.help_requests = []
        self.feedback_responses = []
        self.logged_in_user = ""
        self.selected_module = 1
        self.selected_task = 1
        self.selected_help_request: str = ""
        self.active_help_request: Optional[HelpRequest] = None
        self.start_app()

    # =========== STM-controlled methods =========== ""
    def stm_log(self, text: str):
        print(text)

    def stm_request_resolved(self):
        if self.mqtt_client.resolve_request(self.active_help_request.id):
            previous_claimed_request = self.active_help_request
            self.active_help_request = None
            for i in range(len(self.help_requests)):
                req: HelpRequest = self.help_requests[i]
                if req.id == previous_claimed_request.id:
                    self.help_requests.pop(i)
                    break
            self.show_scene(Scene.MAIN_PAGE)

    def stm_timer_expired(self):
        self.active_help_request.claimed_by = None
        self.active_help_request = None
        if self.current_scene == Scene.HELP_REQUEST:
            self.show_scene(self.current_scene)

    def timer_expired(self):
        self.active_help_request.claimed_by = None
        self.active_help_request = None
        self.show_scene(self.current_scene)

    def stm_receive_feedback(self):
        if len(self.mqtt_client.incoming_feedback) > 0:
            feedback = self.mqtt_client.incoming_feedback.pop()
            idx = self.get_feedback_idx_for_this_group_module_task(feedback.group_number, feedback.module_number,
                                                                   feedback.task_number)
            if idx == -1:
                self.feedback_responses.append(feedback)  # add
            else:
                self.feedback_responses[idx] = feedback  # update
            if self.current_scene == Scene.TASK_MENU and self.selected_module == feedback.module_number and \
                    self.selected_task == feedback.task_number:
                # refresh page if currently in task menu for the right module / task
                self.show_scene(self.current_scene)

    def stm_rec_help_req(self):
        self.help_requests.append(self.mqtt_client.help_request_to_add)
       
        if self.current_scene == Scene.MAIN_PAGE:
            self.show_scene(self.current_scene)
    
    def stm_rem_help_req(self):
        print(self.help_requests)
        for i in range (len(self.help_requests)):
            if self.help_requests[i].id == self.mqtt_client.help_request_to_remove:
                del self.help_requests[i]
                break
        if self.current_scene == Scene.MAIN_PAGE:
            self.show_scene(self.current_scene)

    def stm_cancel_claim(self):
        if self.active_help_request is None:
            return
        if self.mqtt_client.cancel_claim(self.active_help_request.id):
            self.active_help_request.claimed_by = None
            self.active_help_request = None
            if self.current_scene == Scene.HELP_REQUEST:
                self.show_scene(self.current_scene)

    # =========== UI-controlled methods =========== ""
    def start_app(self):
        """ Set up initial scene """
        self.app.setGuiPadding(5, 5)
        self.show_scene(Scene.LOGIN)
        self.app.go()

    def get_feedback_idx_for_this_module_task(self, module_number: int, task_number: int):
        for i in range(len(self.feedback_responses)):
            fr: Feedback = self.feedback_responses[i]
            if fr.module_number == module_number and fr.task_number == task_number:
                return i
        return -1

    def get_feedback_idx_for_this_group_module_task(self, group_number: int, module: int, task: int):
        for i in range(len(self.feedback_responses)):
            fr: Feedback = self.feedback_responses[i]
            if fr.module_number == module and fr.task_number == task and fr.group_number == group_number:
                return i
        return -1

    def add_or_update_feedback_response(self, feedback: Feedback):
        feedback_idx = self.get_feedback_idx_for_this_module_task(feedback.module_number, feedback.task_number)
        if  feedback_idx == -1:  # doesn't exist, add new
            self.feedback_responses.append(feedback)
            return
        self.feedback_responses[feedback_idx] = feedback  # exists, replace

    def set_window_size_and_center(self, x: int, y: int, center=False):
        """ Resize and center window """
        screen_width = self.app.topLevel.winfo_screenwidth()
        screen_height = self.app.topLevel.winfo_screenheight()

        window_x = (screen_width - x) // 2
        window_y = (screen_height - y) // 2
        if center:
            self.app.topLevel.geometry(f"{x}x{y}+{window_x}+{window_y}")
        else:
            self.app.topLevel.geometry(f"{x}x{y}")

    def show_scene(self, scene: int):
        def add_whitespace(desired_row_count: int, current_row_count: int):
            """ Essentially just used to push elements into place """
            rows_to_add = desired_row_count - current_row_count
            for _i in range(rows_to_add):
                self.app.addLabel(str(uuid1()), text="", row=_i + current_row_count + 1, rowspan=1)

        def add_side_menu(back_btn_func=None, desired_rows=5, rowspan=5):
            def show_active_request():
                self.selected_help_request = self.active_help_request.id
                self.show_scene(Scene.HELP_REQUEST)

            self.app.startLabelFrame("Menu", row=0, rowspan=rowspan, column=0, colspan=1)
            self.app.addLabel(f"Logged in as {self.logged_in_user}")
            current_row_count = 1
            if back_btn_func is not None:
                current_row_count = 2
                self.app.addLink("Back", back_btn_func)
            self.app.addLink("Log out", lambda x: self.show_scene(Scene.LOGIN))
            if self.active_help_request is not None:
                self.app.addLink("Show active request", show_active_request)
                current_row_count += 1
            add_whitespace(desired_rows, current_row_count)
            self.app.stopLabelFrame()

        self.app.removeAllWidgets()
        self.current_scene = scene
        if scene == Scene.LOGIN:
            def on_login_click():
                name = self.app.getEntry("TXT_NAME")
                if name == "":
                    self.app.setLabel("LAB_ERROR", "Name cannot be empty")
                    return
                self.logged_in_user = name
                self.mqtt_client.logged_in_ta = name
                self.show_scene(Scene.MAIN_PAGE)

            self.set_window_size_and_center(500, 110)
            self.app.startLabelFrame("Start")
            self.app.setSticky("news")
            self.app.addLabel("LAB_NAME", text="Name", row=0, column=0)
            self.app.addEntry("TXT_NAME", row=0, column=1)
            self.app.addButton("Log in", on_login_click, row=1, column=1)
            self.app.addLabel("LAB_ERROR", text="").config(fg="red")
            self.app.stopLabelFrame()

        elif scene == Scene.MAIN_PAGE:
            def on_task_click(btn_text: str):
                """ Set selected task and module, and switch scene to help request view """
                self.selected_task = int(btn_text.split(" ")[2]) - 1
                self.selected_module = int(btn_text.split(" ")[0][1:])
                self.show_scene(Scene.TASK_MENU)

            def see_request(request_id: str):
                self.selected_help_request = request_id
                self.show_scene(Scene.HELP_REQUEST)

            def add_help_request_frame(_request: HelpRequest):
                self.app.addLabel(
                    f"LAB_GROUP_{_request.id}",
                    f"{_request.queue_pos}: Group {_request.group_number}, module {_request.module_number}, task {_request.task_idx + 1}, time "
                    f"{str(_request.time).split('.')[0]}",
                    column=0, row=self.app.getRow())
                self.app.addButton(f"{_request.id}", see_request, column=1, row=self.app.getRow()-1)
                self.app.setButton(f"{_request.id}", "See request")
                if self.active_help_request and self.active_help_request.id != _request.id:
                    self.app.disableButton(f"{_request.id}")

            self.set_window_size_and_center(500, 500)
            add_side_menu(desired_rows=15, rowspan=10)
            self.app.startLabelFrame("Modules", sticky="news", row=0, rowspan=5, column=1, colspan=3)
            self.app.startTabbedFrame("ModuleTabFrame", sticky="new")
            buttons_per_row = 4
            for module in self.modules:
                self.app.startTab(f"{module.number}")
                self.app.addLabel(f"LAB_MODULE_TITLE_{module.number}", text=f"Module {module.number}: {module.name}",
                                  row=0, colspan=4).config(font=("Helvetica", 14, "bold"))
                row = 1
                col = -1
                for i in range(module.task_count):
                    col += 1
                    if col >= buttons_per_row:
                        col = 0
                        row += 1
                    self.app.addLink(f"M{module.number} task {i + 1}", on_task_click, colspan=1, row=row, column=col)
                add_whitespace(desired_row_count=4, current_row_count=row)
                self.app.stopTab()
            self.app.stopTabbedFrame()
            self.app.setTabbedFrameSelectedTab("ModuleTabFrame", str(self.selected_module))
            self.app.stopLabelFrame()

            self.app.startLabelFrame("Unresolved help requests", sticky="news", row=5, rowspan=5, column=1, colspan=3)
            self.app.startScrollPane("PANE_HELP_REQUESTS")
            for request in sorted(self.help_requests, key=lambda x: x.time, reverse=True):
                if request.status != RequestStatus.COMPLETED:
                    add_help_request_frame(request)
            if len(self.help_requests) == 0:  # To remove warning
                self.app.addLabel(str(uuid1()), "")
            self.app.stopScrollPane()
            self.app.stopLabelFrame()

        elif scene == Scene.HELP_REQUEST:
            current_request: Optional[HelpRequest] = None
            for request in self.help_requests:
                if request.id == self.selected_help_request:
                    current_request = request
                    break
            if current_request is None:
                print("SOMETHING WENT WRONG, COULDN'T FIND REQUEST WITH ID " + str(self.selected_help_request))
                self.show_scene(Scene.MAIN_PAGE)
            request_group: Optional[Group] = None
            for group in self.groups:
                if group.number == current_request.group_number:
                    request_group = group
                    break

            def on_claim():
                if current_request.claimed_by is None:
                    current_request.claimed_by = self.logged_in_user  # claim
                    current_request.status = RequestStatus.CONFIRMED
                    if self.mqtt_client.claim_request(current_request, self.logged_in_user):
                        self.active_help_request = current_request
                        self.stm_teaching_assistant.send("claim_button")
                        self.show_scene(self.current_scene)
                    else:
                        print("Failed to send mqtt claim request")
                else:
                    # cancel claim
                    print("cancelling claim")
                    self.stm_teaching_assistant.send("cancel_claim")

            def on_resolve_claim():
                current_request.status = RequestStatus.COMPLETED
                self.active_help_request = current_request
                self.stm_teaching_assistant.send("resolve_button")

            self.set_window_size_and_center(500, 250)
            add_side_menu(lambda x: self.show_scene(Scene.MAIN_PAGE))
            self.app.startLabelFrame(f"Help request", sticky="news", row=0, rowspan=6, column=1, colspan=3)
            self.app.addLabel("LAB_COMMENT", text=f""" "{current_request.comment}" """)
            self.app.addLabel("LAB_GROUP", text=f"- Group {request_group.number}, table {request_group.table}")
            self.app.addLabel("LAB_EMPTY", text="")
            self.app.addLabel("LAB_MODULE_AND_TASK", text=f"Module {current_request.module_number}, task {current_request.task_idx + 1}")
            self.app.addLabel("LAB_IS_ONLINE", text=f"Online? {'Yes' if current_request.is_online else 'No'}")
            self.app.addLabel("LAB_ZOOM_URL", text=f"Zoom link: {'Not provided' if current_request.zoom_url == '' else current_request.zoom_url}")
            self.app.addLabel("LAB_CLAIMED", text=f"Claimed by: {'Nobody' if current_request.claimed_by is None else current_request.claimed_by}")
            if current_request.status == RequestStatus.COMPLETED:
                self.app.addLabel("LAB_COMPLETED", "This request has been resolved.")
                self.app.stopLabelFrame()
                return
            self.app.addButton("BTN_CLAIM", on_claim)
            self.app.addButton("BTN_RESOLVE", on_resolve_claim).config(text="Resolve")
            if current_request.claimed_by is None:
                self.app.setButton("BTN_CLAIM", "Claim")
            elif current_request.claimed_by == self.logged_in_user:
                self.app.setButton("BTN_CLAIM", "Cancel claim")
            else:
                self.app.setButton("BTN_CLAIM", "Claim")
                self.app.disableButton("BTN_CLAIM")
                self.app.addLabel("LAB_WHY_DISABLED", text="Request is already claimed").config(fg="red")
            self.app.stopLabelFrame()

        elif scene == Scene.TASK_MENU:
            # gather data for display
            ratings = {"Easy": 0, "Medium": 0, "Hard": 0}
            feedback_for_this_task = []
            for feedback in self.feedback_responses:
                if feedback.module_number == self.selected_module and feedback.task_number == self.selected_task:
                    feedback_for_this_task.append(feedback)
                    ratings[feedback.difficulty] += 1
            groups_completed = ratings["Easy"] + ratings["Medium"] + ratings["Hard"]
            groups_completed_percent = 0
            avg_rating = 0
            if groups_completed > 0:
                groups_completed_percent = round(groups_completed * 100 / len(self.groups), 2)
                avg_rating = (ratings["Easy"] + (2 * ratings["Medium"]) + (3 * ratings["Hard"])) / groups_completed

            self.set_window_size_and_center(500, 350)
            add_side_menu(lambda x: self.show_scene(Scene.MAIN_PAGE))
            self.app.startLabelFrame(f"Feedback for task {self.selected_task + 1} module {self.selected_module}",
                                     sticky="news", row=0, rowspan=6, column=1, colspan=3)
            self.app.addLabel("LAB_GROUPS_COMPLETED", text=f"{groups_completed_percent}% of groups completed")
            self.app.addLabel("LAB_RATINGS_TITLE", text="Ratings:")
            self.app.addLabel("LAB_RATINGS", text=f"Easy: {ratings['Easy']}, Medium: {ratings['Medium']}, Hard: {ratings['Hard']}")
            self.app.addLabel("LAB_AVERAGE_RATING", text=f"Average rating: {round(avg_rating, 2)}")

            self.app.startScrollPane("PANE_FEEDBACK")
            for feedback in feedback_for_this_task:
                self.app.addLabel(str(uuid1()), f""" "{feedback.comment}"\n-Group {feedback.group_number} """)
            if len(feedback_for_this_task) == 0:  # To remove warning
                self.app.addLabel(str(uuid1()), "")
            self.app.stopScrollPane()
            self.app.stopLabelFrame()
        else:
            pass


if __name__ == "__main__":
    ui = UserInterface(modules=sorted(import_modules(), key=lambda m: m.number),
                       groups=sorted(import_groups(), key=lambda g: g.number))
    ui.driver.stop()
    ui.mqtt_client.client.disconnect()
