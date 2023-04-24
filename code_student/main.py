from appJar import gui
import code_student.gui_elems as elems
from enum import Enum

from code_student.module import Module


class MQTTClient:
    def __init__(self):
        pass

    def login(self, group_name: str) -> bool:
        """ Try logging in as group. Returns True if succeeded, false otherwise """
        return False


class Scene(Enum):
    LOGIN: int = 0
    MAIN_PAGE: int = 1
    HELP_REQUEST: int = 2


class UserInterface:
    def __init__(self, modules: list):
        self.app = gui("Student Client", "1x1")  # size is set in show_scene() method
        self.mqtt_client = MQTTClient()
        self.current_scene = -1
        self.modules = modules
        self.logged_in_user = ""
        self.selected_module = 1
        self.selected_task = 1
        self.start_app()


    def show_error(self, message: str):
        self.app.setLabel(elems.LAB_ERROR, message)
        self.app.showLabel(elems.LAB_ERROR)

    def start_app(self):
        """ Set up initial scene """
        self.app.setGuiPadding(5, 5)
        self.show_scene(Scene.LOGIN)
        self.app.go()

    def create_request_form(self, module: int, task: int):
        # comment
        self.app.addEntry(f"MOD{module}_TASK{task}")
        self.app.setEntryDefault(f"MOD{module}_TASK{task}", "Comment...")

    def set_window_size_and_center(self, x: int, y: int):
        """ Resize and center window """
        screen_width = self.app.topLevel.winfo_screenwidth()
        screen_height = self.app.topLevel.winfo_screenheight()

        window_x = (screen_width - x) // 2
        window_y = (screen_height - y) // 2

        self.app.topLevel.geometry(f"{x}x{y}+{window_x}+{window_y}")

    def show_scene(self, scene: int):
        def add_side_menu(back_btn_func=None):
            self.app.startLabelFrame("Menu", row=0, rowspan=5, column=0, colspan=1)
            self.app.addLabel(f"Logged in as {self.logged_in_user}")
            if back_btn_func is not None:
                self.app.addLink("Back", back_btn_func)
            self.app.addLink("Log out", lambda x: self.show_scene(Scene.LOGIN))
            if back_btn_func is None:
                self.app.addLabel(f"MENU_WHITESPACE_1", text="")
            self.app.addLabel(f"MENU_WHITESPACE_2", text="")
            self.app.addLabel(f"MENU_WHITESPACE_3", text="")
            self.app.stopLabelFrame()

        self.app.removeAllWidgets()
        self.current_scene = scene
        if scene == Scene.LOGIN:
            def on_login_click():
                """ Try logging in """
                group_name = self.app.getEntry(elems.TXT_GROUP_NAME)
                if group_name != "":
                    if not self.mqtt_client.login(group_name):
                        self.show_error("")
                    self.logged_in_user = group_name
                    # TODO: do some MQTT stuff ?
                    self.show_scene(Scene.MAIN_PAGE)
                    return
                self.show_error("Error: Invalid group name")

            self.set_window_size_and_center(500, 100)
            self.app.startLabelFrame("Start")
            self.app.setSticky("nwe")  # on resize, stretch from north-west to east
            self.app.addLabel("l_group", "Group name", 0, 0)
            self.app.addEntry(elems.TXT_GROUP_NAME, 0, 1)
            self.app.addLabel(elems.LAB_ERROR, "Error, something went wrong", 1, 1)
            self.app.setLabelFg(elems.LAB_ERROR, "red")
            self.app.hideLabel(elems.LAB_ERROR)
            self.app.addButton(elems.BTN_LOGIN, on_login_click, 2, 1)
            self.app.stopLabelFrame()

        elif scene == Scene.MAIN_PAGE:
            def on_task_click(btn_text: str):
                """ Set selected task and module, and switch scene to help request view """
                self.selected_task = int(btn_text.split(" ")[2]) - 1
                self.selected_module = int(btn_text.split(" ")[0][1:])
                self.show_scene(Scene.HELP_REQUEST)

            self.set_window_size_and_center(500, 250)
            add_side_menu()
            self.app.startLabelFrame("Modules", sticky="news", row=0, rowspan=5, column=1, colspan=3)
            self.app.startTabbedFrame("ModuleTabFrame", sticky="new")
            buttons_per_row = 4
            for module in self.modules:
                self.app.startTab(f"{module.number}")
                row = 0
                col = -1
                for i in range(module.task_count):
                    col += 1
                    if col >= buttons_per_row:
                        col = 0
                        row += 1
                    # OBS: if you change the text, you must also update the parsing in the self.on_task_click method
                    self.app.addLink(f"M{module.number} task {i+1}", on_task_click, column=col, row=row)
                self.app.stopTab()
            self.app.stopTabbedFrame()
            self.app.setTabbedFrameSelectedTab("ModuleTabFrame", str(self.selected_module))
            self.app.stopLabelFrame()
        elif scene == Scene.HELP_REQUEST:
            def on_submit():
                # TODO: mqtt stuff
                print("sending mqtt request")
                self.app.setLabel("LAB_SENT_STATUS", "Request status: SENT")
                self.app.setLabelFg("LAB_SENT_STATUS", "orange")
                self.app.setButton("BTN_SUBMIT", "Update help request")

            add_side_menu(lambda x: self.show_scene(Scene.MAIN_PAGE))
            self.app.startLabelFrame(f"Request help with module {self.selected_module} task {self.selected_task + 1}",
                                     sticky="news", row=0, rowspan=6, column=1, colspan=3)
            self.app.addCheckBox("Online")
            self.app.addTextArea("Comment", text="What do you need help with?")
            self.app.addButton("BTN_SUBMIT", on_submit)
            self.app.setButton("BTN_SUBMIT", "Send help request")
            self.app.addLabel("LAB_SENT_STATUS", text="Request status: NOT SENT")
            self.app.setLabelFg("LAB_SENT_STATUS", "red")
            self.app.stopLabelFrame()
        else:
            pass


def create_modules():
    """ Generate initial modules """
    return [
        Module(1, "Setup", 3),
        Module(2, "Modeling", 5),
        Module(3, "State Machines", 2),
        Module(4, "Requirements", 4),
        Module(5, "State Machines in Python", 3),
        Module(6, "Agile Development", 4),
        Module(7, "Communication", 4),
        Module(8, "Sequence Diagrams", 2),
        Module(9, "Components", 5),
    ]


if __name__ == "__main__":
    m = create_modules()
    ui = UserInterface(modules=m)
