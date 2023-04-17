from appJar import gui
import code_student.gui_elems as elems
from enum import Enum


class MQTTClient:
    def __init__(self):
        pass

    def login(self, group_name: str) -> bool:
        """ Try logging in as group. Returns True if succeeded, false otherwise """
        return False


class Scene(Enum):
    LOGIN: int = 0
    MAIN_PAGE: int = 1


class UserInterface:
    def __init__(self):
        self.app = gui("Student Client", "500x150")
        self.mqtt_client = MQTTClient()
        self.current_scene = -1
        self.start_app()

    def show_error(self, message: str):
        self.app.setLabel(elems.LAB_ERROR, message)
        self.app.showLabel(elems.LAB_ERROR)

    def on_login_click(self):
        """ Try logging in """
        group_name = self.app.getEntry(elems.TXT_GROUP_NAME)
        if group_name != "":
            if not self.mqtt_client.login(group_name):
                self.show_error("")
            self.show_scene(Scene.MAIN_PAGE)
            return
        self.show_error("Error: Invalid group name")

    def start_app(self):
        """ Set up initial scene """
        self.app.setGuiPadding(5, 5)
        self.show_scene(Scene.LOGIN)
        self.app.go()

    def show_scene(self, scene: int):
        self.app.removeAllWidgets()
        self.current_scene = scene
        if scene == Scene.LOGIN:
            self.app.startLabelFrame("Start")
            self.app.setSticky("ew")  # stretch to fit width, align center
            self.app.addLabel("l_group", "Group name", 0, 0)
            self.app.addEntry(elems.TXT_GROUP_NAME, 0, 1)
            self.app.addLabel(elems.LAB_ERROR, "Error, something went wrong", 1, 1)
            self.app.setLabelFg(elems.LAB_ERROR, "red")
            self.app.hideLabel(elems.LAB_ERROR)
            self.app.addButton(elems.BTN_LOGIN, self.on_login_click, 2, 1)
            self.app.stopLabelFrame()
        elif scene == Scene.MAIN_PAGE:
            # TODO: Set up scene
            pass
        else:
            pass


if __name__ == "__main__":
    UserInterface()
