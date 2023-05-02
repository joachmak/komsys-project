import json
from threading import Thread
from typing import Optional

from appJar import gui
from enum import Enum
from uuid import uuid1

from stmpy import Machine, Driver

from code_student.stm_utils import get_stm_transitions, get_stm_states
from common.feedback import Feedback
from common.io_utils import import_modules, import_groups
from common.help_request import HelpRequest
import paho.mqtt.client as mqtt

from common.mqtt_utils import BROKER, PORT, TOPIC_QUEUE, TOPIC_TA, RequestWrapper, TYPE_ADD_HELP_REQUEST, \
    TYPE_CANCEL_HELP_REQUEST, TOPIC_BASE, parse_help_request, TYPE_SEND_FEEDBACK, TOPIC_TASK, TYPE_CLAIM_REQUEST, \
    parse_claim_request, TYPE_CONFIRM_CLAIM


def clear_retained_messages(client: mqtt.Client):
    client.publish(TOPIC_QUEUE, payload=None, retain=True)
    client.publish(TOPIC_TA, payload=None, retain=True)


class MQTTClient:
    def __init__(self, stm: Machine):
        self.client = mqtt.Client()
        self.queue_pos = 1
        self.stm = stm
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        print(f"Trying to connect to {BROKER}")
        self.client.connect(BROKER, PORT)
        clear_retained_messages(self.client)  # Remove in prod
        self.client.subscribe(TOPIC_QUEUE)
        self.ta_claiming_request = None
        self.request_claimed = None
        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        print(format(mqtt.connack_string(rc)))

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        print("on_message(): topic: {}, data: {}".format(msg.topic, msg.payload))
        request_type = int(str(msg.payload).split(": ")[1][0])
        payload = str(msg.payload).replace("\\", "")
        if request_type == TYPE_ADD_HELP_REQUEST:
            # Add HelpRequest
            request: HelpRequest = parse_help_request(payload)
            print(request.id)
            # TODO: adjust queue
        elif request_type == TYPE_CANCEL_HELP_REQUEST:
            # Cancel HelpRequest, TODO: adjust queue
            print("Cancelling request")
        elif request_type == TYPE_CLAIM_REQUEST:
            print("Received claim request from ta")
            if self.ta_claiming_request is not None:
                return
            request_id, ta_name = parse_claim_request(payload)
            self.ta_claiming_request = ta_name
            self.request_claimed = request_id
            self.stm.send("sig_receive_request_claim")


    def request_help(self, request: HelpRequest) -> bool:
        """ Send help request """
        print(f"Sending help request")
        req_body = RequestWrapper(TYPE_ADD_HELP_REQUEST, request.payload()).payload()
        return self.client.publish(TOPIC_QUEUE, payload=req_body, retain=True).is_published()

    def cancel_request(self, request_id: str) -> bool:
        """ Cancel help request by id """
        print(f"Cancelling help request with id {request_id}")
        req_body = RequestWrapper(TYPE_CANCEL_HELP_REQUEST, str({"id": request_id})).payload()
        return self.client.publish(TOPIC_QUEUE, payload=req_body).is_published()

    def send_feedback(self, feedback: Feedback) -> bool:
        req_body = RequestWrapper(TYPE_SEND_FEEDBACK, feedback.payload())
        return self.client.publish(TOPIC_TASK, payload=req_body.payload()).is_published()

    def confirm_claim(self, ta: str) -> bool:
        print("Confirming claim")
        req_body = RequestWrapper(TYPE_CONFIRM_CLAIM, str({'ta': ta}))
        return self.client.publish(TOPIC_QUEUE, payload=req_body.payload()).is_published()


class Scene(Enum):
    LOGIN: int = 0
    MAIN_PAGE: int = 1
    HELP_REQUEST: int = 2
    MARK_TASK_AS_DONE: int = 3
    TASK_MENU: int = 4


class UserInterface:
    def __init__(self, modules: list, groups: list):
        self.app = gui("Student Client", "1x1")  # size is set in show_scene() method

        self.stm_help_request = Machine(name="stm_student_help_request", transitions=get_stm_transitions(), obj=self, states=get_stm_states())
        self.driver = Driver()
        self.driver.add_machine(self.stm_help_request)

        self.mqtt_client = MQTTClient(self.stm_help_request)

        self.current_scene = -1
        self.modules = modules
        self.groups = groups
        self.feedback_responses = []
        self.logged_in_user = ""
        self.selected_module = 1
        self.selected_task = 1
        self.active_help_request: Optional[HelpRequest] = None
        self.driver.start()
        self.start_app()
        self.logged_in_group_number = -1

    # ======== STM-controlled methods ========
    def stm_log(self, text: str):
        print(self.current_scene)
        print(text)

    def stm_request_help(self):
        # take active help request and send mqtt requests
        print("inside stm method for sending request")
        success = self.mqtt_client.request_help(self.active_help_request)
        # if mqtt request fails, set it to None and refresh scene
        if not success:
            print("MQTT request failed!")
            self.active_help_request = None
            if self.current_scene == Scene.HELP_REQUEST:
                # if user is watching the help request page, refresh the scene
                self.show_scene(self.current_scene)

    def stm_cancel_help_request(self):
        # take active help request send mqtt request cancelling the help request
        success = self.mqtt_client.cancel_request(self.active_help_request.id)
        if success:
            self.active_help_request = None
            self.show_scene(self.current_scene)

    def stm_receive_request_claim(self):
        print("stm received request claim")
        if self.active_help_request is None or self.active_help_request.id != self.mqtt_client.request_claimed:
            # the request claim was not meant for this student. If it was, TA will time out anyway
            print("the request claim was not for this student")
            self.mqtt_client.ta_claiming_request = None
            self.mqtt_client.request_claimed = None
            return
        if self.active_help_request.claimed_by == "":
            ta = self.mqtt_client.ta_claiming_request
            print(f"Ta {ta} wants to claim current help request, and we're gonna let him")
            if self.mqtt_client.confirm_claim(ta):
                self.active_help_request.claimed_by = ta
                if self.current_scene == Scene.HELP_REQUEST:
                    # if user is watching the help request page, refresh the scene
                    self.show_scene(self.current_scene)
        print("Hmm, none of the ifs were triggered...")
        print(f"Active help request is claimed by: {self.active_help_request.claimed_by}")



    # ======== UI-controlled methods ========
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

    def add_or_update_feedback_response(self, feedback: Feedback):
        if not self.mqtt_client.send_feedback(feedback):
            print("failed to send feedback via mqtt")
            return
        feedback_idx = self.get_feedback_idx_for_this_module_task(feedback.module_number, feedback.task_number)
        if feedback_idx == -1:  # doesn't exist, add new
            self.feedback_responses.append(feedback)
            # TODO: reflect in UI that feedback wasn't sent
            return
        self.feedback_responses[feedback_idx] = feedback  # exists, replace

    def create_request_form(self, module: int, task: int):
        # comment
        self.app.addEntry(f"MOD{module}_TASK{task}")
        self.app.setEntryDefault(f"MOD{module}_TASK{task}", "Comment...")

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

        def add_side_menu(back_btn_func=None, desired_rows=5):
            def show_active_request():
                self.selected_task = self.active_help_request.task_idx
                self.selected_module = self.active_help_request.module_number
                self.show_scene(Scene.HELP_REQUEST)

            self.app.startLabelFrame("Menu", row=0, rowspan=5, column=0, colspan=1)
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
                group_name = self.app.getOptionBox("Group")
                self.logged_in_user = group_name
                self.logged_in_group_number = int(group_name.split(" ")[1][:-1])
                self.show_scene(Scene.MAIN_PAGE)

            self.set_window_size_and_center(500, 100)
            self.app.startLabelFrame("Start")
            self.app.setSticky("nwe")  # on resize, stretch from north-west to east
            self.app.addLabelOptionBox("Group", [f"Group {group.number}, table {group.table}" for group in self.groups])
            self.app.addButton("BTN_LOGIN", on_login_click, 1, 0)
            self.app.setButton("BTN_LOGIN", "Log in")
            self.app.stopLabelFrame()

        elif scene == Scene.MAIN_PAGE:
            def on_task_click(btn_text: str):
                """ Set selected task and module, and switch scene to help request view """
                self.selected_task = int(btn_text.split(" ")[2]) - 1
                self.selected_module = int(btn_text.split(" ")[0][1:])
                self.show_scene(Scene.TASK_MENU)

            self.set_window_size_and_center(500, 250)
            add_side_menu()
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

        elif scene == Scene.HELP_REQUEST:
            def on_help_submit():
                if self.active_help_request is None:
                    # Send new help request
                    comment = self.app.getTextArea("LAB_COMMENT")
                    is_online = self.app.getCheckBox("Online")
                    zoom_url = self.app.getEntry("TXT_ZOOM")
                    # TODO: validation (e.g. must have zoom link if is_online, must have comment)
                    self.active_help_request = HelpRequest(self.logged_in_group_number, self.selected_module, self.selected_task, is_online,
                                                           zoom_url, comment)
                    self.stm_help_request.send("click")
                    self.active_help_request.queue_pos = 69  # TODO: find queue position
                else:
                    # Cancel help request
                    self.stm_help_request.send("click")
                self.show_scene(Scene.HELP_REQUEST)

            self.set_window_size_and_center(500, 300)
            add_side_menu(lambda x: self.show_scene(Scene.TASK_MENU), desired_rows=6)
            self.app.startLabelFrame(f"Request help with module {self.selected_module} task {self.selected_task + 1}",
                                     sticky="news", row=0, rowspan=6, column=1, colspan=3)
            self.app.addCheckBox("Online")
            self.app.addEntry("TXT_ZOOM")
            self.app.setEntry("TXT_ZOOM", "Zoom meeting url (if online)")
            self.app.addTextArea("LAB_COMMENT", text="")
            self.app.addButton("BTN_SUBMIT", on_help_submit)
            self.app.setButton("BTN_SUBMIT", "Send help request")
            self.app.addLabel("LAB_SENT_STATUS", text="Request status: NOT SENT")
            if self.active_help_request is None:
                self.app.setTextArea("LAB_COMMENT", text="What do you need help with?")
                self.app.setLabel("LAB_SENT_STATUS", text="Request status: NOT SENT")
                self.app.setLabelFg("LAB_SENT_STATUS", "red")
            elif self.active_help_request.claimed_by == "":
                self.app.setTextArea("LAB_COMMENT", text=self.active_help_request.comment)
                self.app.setCheckBox("Online", ticked=self.active_help_request.is_online)
                self.app.setEntry("TXT_ZOOM", text=self.active_help_request.zoom_url)
                self.app.setLabel("LAB_SENT_STATUS", text="Request status: SENT")
                self.app.setButton("BTN_SUBMIT", "Cancel help request")
                self.app.setLabelFg("LAB_SENT_STATUS", "orange")
                self.app.addLabel("LAB_QUEUE_POS", text=f"Position in queue: {self.active_help_request.queue_pos}")
            else:
                self.app.setTextArea("LAB_COMMENT", text=self.active_help_request.comment)
                self.app.setCheckBox("Online", ticked=self.active_help_request.is_online)
                self.app.setEntry("TXT_ZOOM", text=self.active_help_request.zoom_url)
                self.app.disableTextArea("LAB_COMMENT")
                self.app.disableCheckBox("Online")
                self.app.disableEntry("TXT_ZOOM")
                self.app.setLabel("LAB_SENT_STATUS", text=f"Request status: CONFIRMED by {self.active_help_request.claimed_by}")
                self.app.setLabelFg("LAB_SENT_STATUS", "green")
                self.app.setButton("BTN_SUBMIT", "Cancel help request")
                self.app.disableButton("BTN_SUBMIT")

            self.app.stopLabelFrame()

        elif scene == Scene.MARK_TASK_AS_DONE:
            def on_task_done_submit():
                difficulty = self.app.getRadioButton("RAD_DIFFICULTY")
                feedback = self.app.getTextArea("TXT_FEEDBACK")
                feedback_response = Feedback(self.logged_in_group_number, self.selected_module, self.selected_task,
                                             feedback, difficulty)
                self.add_or_update_feedback_response(feedback_response)
                self.show_scene(self.current_scene)

            self.set_window_size_and_center(500, 300)
            add_side_menu(lambda x: self.show_scene(Scene.TASK_MENU), desired_rows=6)
            self.app.startLabelFrame(f"Mark task {self.selected_task + 1} module {self.selected_module} as done",
                                     sticky="news", row=0, rowspan=6, column=1, colspan=3)
            self.app.addLabel("LAB_RATING", text="Difficulty rating:")
            self.app.addRadioButton("RAD_DIFFICULTY", "Easy")
            self.app.addRadioButton("RAD_DIFFICULTY", "Medium")
            self.app.addRadioButton("RAD_DIFFICULTY", "Hard")
            self.app.addTextArea("TXT_FEEDBACK", text="")
            self.app.addButton("BTN_SUBMIT", on_task_done_submit)

            feedback_idx = self.get_feedback_idx_for_this_module_task(self.selected_module, self.selected_task)
            if feedback_idx != -1:
                feedback = self.feedback_responses[feedback_idx]
                self.app.setButton("BTN_SUBMIT", "Update task feedback")
                self.app.addLabel("LAB_DONE_STATUS", text="Status: Done")
                self.app.setLabelFg("LAB_DONE_STATUS", "green")
                self.app.setRadioButton("RAD_DIFFICULTY", feedback.difficulty)
                self.app.setTextArea("TXT_FEEDBACK", text=feedback.comment)
            else:
                self.app.setButton("BTN_SUBMIT", "Mark as done")
                self.app.addLabel("LAB_DONE_STATUS", text="Status: NOT DONE")
                self.app.setLabelFg("LAB_DONE_STATUS", "red")
                self.app.setTextArea("TXT_FEEDBACK", "Feedback...")
            self.app.stopLabelFrame()

        elif scene == Scene.TASK_MENU:
            def has_selected_task_an_active_request() -> bool:
                if self.active_help_request is None:
                    return False
                if self.selected_task != self.active_help_request.task_idx:
                    return False
                if self.selected_module != self.active_help_request.module_number:
                    return False
                return True

            self.set_window_size_and_center(500, 250)
            add_side_menu(lambda x: self.show_scene(Scene.MAIN_PAGE))
            self.app.startLabelFrame(f"Options for module {self.selected_module} task {self.selected_task + 1}",
                                     sticky="news", row=0, rowspan=6, column=1, colspan=3)
            feedback_idx = self.get_feedback_idx_for_this_module_task(self.selected_module, self.selected_task)
            if feedback_idx != -1:
                feedback = self.feedback_responses[feedback_idx]
                self.app.addLabel("LAB_FEEDBACK_STATUS", text=f"Status: DONE, difficulty: {feedback.difficulty}").config(fg="green")
            else:
                self.app.addLabel("LAB_FEEDBACK_STATUS", text=f"Status: UNFINISHED").config(fg="red")
            self.app.addButton("BTN_MARK_AS_DONE", lambda x: self.show_scene(Scene.MARK_TASK_AS_DONE))
            self.app.addButton("BTN_REQUEST_HELP", lambda x: self.show_scene(Scene.HELP_REQUEST))
            self.app.setButton("BTN_MARK_AS_DONE", "Mark task as done" if feedback_idx == -1 else "Update task feedback")
            self.app.setButton("BTN_REQUEST_HELP", "Send help request")
            if self.active_help_request is not None and not has_selected_task_an_active_request():
                self.app.disableButton("BTN_REQUEST_HELP")
                self.app.addLabel("LAB_ACTIVE_REQUEST", text="You can only have 1 active request at a time") \
                    .config(foreground="red")
                add_whitespace(5, 3)
            elif has_selected_task_an_active_request():
                self.app.setButton("BTN_REQUEST_HELP", "See active help request")
                add_whitespace(5, 2)
            else:
                add_whitespace(5, 2)
            self.app.stopLabelFrame()
        else:
            pass


if __name__ == "__main__":
    ui = UserInterface(modules=sorted(import_modules(), key=lambda m: m.number),
                       groups=sorted(import_groups(), key=lambda g: g.number))
    ui.driver.stop()
    ui.mqtt_client.client.disconnect()
