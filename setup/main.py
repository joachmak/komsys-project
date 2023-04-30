from typing import Optional, List

from appJar import gui
from os import path
import json
import code_student.gui_elems as elems
from enum import Enum
from uuid import uuid1

from code_student.module import Module
from code_student.request_form import HelpRequest


DATA_FILEPATH = path.join("..", "data")


class MQTTClient:
    def __init__(self):
        pass

    def login(self, group_name: str) -> bool:
        """ Try logging in as group. Returns True if succeeded, false otherwise """
        return False


class Scene(Enum):
    MAIN_MENU: int = 0
    MODULES: int = 1
    GROUPS: int = 2
    SAVE_EDIT_MODULE: int = 3


def import_modules():
    try:
        with open(path.join(DATA_FILEPATH, "modules.json"), "r") as f:
            loaded_data = json.load(f)
            loaded_modules = []
            for module in loaded_data:
                loaded_modules.append(Module(module["number"], module["name"], module["task_count"]))
            return loaded_modules
    except OSError:
        return None


class UserInterface:
    def __init__(self, modules: list):
        self.app = gui("Configuration App", "1x1")  # size is set in show_scene() method
        self.mqtt_client = MQTTClient()
        self.current_scene = -1
        self.modules = import_modules()
        self.module_to_edit = -1
        self.is_editing = False
        self.start_app()

    def show_error(self, message: str):
        self.app.setLabel(elems.LAB_ERROR, message)
        self.app.showLabel(elems.LAB_ERROR)

    def start_app(self):
        """ Set up initial scene """
        self.app.setGuiPadding(5, 5)
        self.show_scene(Scene.MAIN_MENU)
        self.app.go()

    def get_module(self, number: int):
        for _module in self.modules:
            if _module.number == self.module_to_edit:
                return _module
        return None

    def swap_module(self, old_module_number: int, new_module: Module):
        for i in range(len(self.modules)):
            _m = self.modules[i]
            if old_module_number == _m.number:
                self.modules[i] = new_module
                return

    def persist_modules(self):
        modules = []
        for module in self.modules:
            modules.append({"name": module.name, "number": module.number, "task_count": module.task_count})
        with open(path.join(DATA_FILEPATH, "modules.json"), "w") as f:
            json.dump(modules, f)
        self.show_scene(Scene.MODULES)

    def set_window_size_and_center(self, x: int, y: int):
        """ Resize and center window """
        screen_width = self.app.topLevel.winfo_screenwidth()
        screen_height = self.app.topLevel.winfo_screenheight()

        window_x = (screen_width - x) // 2
        window_y = (screen_height - y) // 2

        self.app.topLevel.geometry(f"{x}x{y}+{window_x}+{window_y}")

    def get_next_vacant_module_number(self):
        num_arr = [0] * 100
        for _module in self.modules:
            num_arr[_module.number - 1] = 1
        for i in range(len(num_arr)):
            if num_arr[i] == 0:
                return i + 1
        return -1  # No vacant spots, very unlikely, won't bother handling it

    def show_scene(self, scene: int):
        def add_whitespace(desired_row_count: int, current_row_count: int):
            """ Essentially just used to push elements into place """
            rows_to_add = desired_row_count - current_row_count
            for _i in range(rows_to_add):
                self.app.addLabel(str(uuid1()), text="", row=_i + current_row_count + 1, rowspan=1)

        def add_side_menu(back_btn_func=None, desired_rows=15):
            self.app.startLabelFrame("Menu", row=0, rowspan=5, column=0, colspan=1)
            current_row_count = 0
            if back_btn_func is not None:
                current_row_count = 1
                self.app.addLink("Back", back_btn_func)
            add_whitespace(desired_rows, current_row_count)
            self.app.stopLabelFrame()

        self.app.removeAllWidgets()
        self.current_scene = scene
        if scene == Scene.MAIN_MENU:
            self.set_window_size_and_center(500, 100)
            self.app.startLabelFrame("Options")
            self.app.setSticky("nwe")  # on resize, stretch from north-west to east
            self.app.addLink("Edit modules", lambda _: self.show_scene(Scene.MODULES))
            self.app.addLink("Edit groups", lambda _: self.show_scene(Scene.GROUPS))
            self.app.stopLabelFrame()
        elif scene == Scene.MODULES:
            def delete_module(num: int):
                self.modules = [_module for _module in self.modules if _module.number != num]
                self.persist_modules()

            def on_edit_module(module_num: int):
                self.module_to_edit = module_num
                self.is_editing = True
                self.show_scene(Scene.SAVE_EDIT_MODULE)

            def on_add_module():
                self.is_editing = False
                self.show_scene(Scene.SAVE_EDIT_MODULE)

            def add_module_frame(_module: Module):
                self.app.startFrame(f"MODFRAME_{_module.number}_{_module.name}", colspan=3, rowspan=1)
                self.app.setSticky("nw")
                self.app.addLabel(f"{_module.number}: {_module.name}, {_module.task_count} tasks", column=0, row=0)
                self.app.addLink(f"Edit module {_module.number}", lambda x: on_edit_module(_module.number), column=1, row=0)
                self.app.addLink(f"Delete module {_module.number}", lambda x: delete_module(_module.number), column=2, row=0)
                self.app.stopFrame()

            self.set_window_size_and_center(700, 600)
            add_side_menu(lambda _: self.show_scene(Scene.MAIN_MENU))
            self.app.startLabelFrame("Modules", column=1, row=0, rowspan=4)
            self.app.setSticky("nwe")  # on resize, stretch from north-west to east
            max_rows = 15
            for module in sorted(self.modules, key=lambda _m: _m.number):
                add_module_frame(module)
            self.app.addLink("+ Add module", on_add_module)
            add_whitespace(max_rows, len(self.modules) + 1)
            self.app.stopLabelFrame()

        elif scene == Scene.SAVE_EDIT_MODULE:
            def on_submit():
                number = self.app.getEntry("LAB_NUMBER")
                name = self.app.getEntry("LAB_NAME")
                task_count = self.app.getEntry("LAB_TASK_COUNT")
                if not number.isnumeric():
                    self.app.setLabel("LAB_ERROR", "Module number field is not numeric")
                    return
                if int(number) > 100 or int(number) < 1:
                    self.app.setLabel("LAB_ERROR", "Module number must be between 1 and 100")
                    return
                if not task_count.isnumeric():
                    self.app.setLabel("LAB_ERROR", "Module task count is not numeric")
                    return
                if name == "":
                    self.app.setLabel("LAB_ERROR", "Invalid module name")
                    return
                # Avoid that two modules end up with the same task number
                for _module in self.modules:
                    if _module.number == int(number) and (not self.is_editing or _module.number != self.module_to_edit):
                        self.app.setLabel("LAB_ERROR", "Module number already taken")
                        return
                if self.is_editing:
                    self.swap_module(self.module_to_edit, Module(int(number), name, int(task_count)))
                else:
                    self.modules.append(Module(int(number), name, int(task_count)))
                self.persist_modules()
                self.show_scene(Scene.MODULES)

            self.set_window_size_and_center(500, 300)
            add_side_menu(lambda _: self.show_scene(Scene.MODULES), desired_rows=6)
            if self.is_editing:
                self.app.startLabelFrame(f"Update module {self.module_to_edit}", sticky="news", row=0, rowspan=6, column=1, colspan=3)
            else:
                self.app.startLabelFrame(f"Add new module", sticky="news", row=0, rowspan=6, column=1, colspan=3)
            self.app.addLabel("Module number:")
            self.app.addEntry("LAB_NUMBER")
            self.app.addLabel("Module name:")
            self.app.addEntry("LAB_NAME")
            self.app.addLabel("Task count:")
            self.app.addEntry("LAB_TASK_COUNT")
            self.app.addButton("BTN_SUBMIT_MODULE", on_submit)
            self.app.addLabel("LAB_ERROR", "").config(fg="red")
            if self.is_editing:
                self.app.setButton("BTN_SUBMIT_MODULE", "Update module")
                # find current module
                current_module = self.get_module(self.module_to_edit)
                self.app.setEntry("LAB_NUMBER", current_module.number)
                self.app.setEntry("LAB_NAME", current_module.name)
                self.app.setEntry("LAB_TASK_COUNT", current_module.task_count)
            else:
                self.app.setButton("BTN_SUBMIT_MODULE", "Add module")
                self.app.setEntry("LAB_NUMBER", self.get_next_vacant_module_number())
            add_whitespace(10, 7)
            self.app.stopLabelFrame()

        elif scene == Scene.GROUPS:
            pass
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
