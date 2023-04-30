import json
from os import path

from common.group import Group
from common.module import Module


DATA_FILEPATH = path.join("..", "data")


def import_modules():
    try:
        with open(path.join(DATA_FILEPATH, "modules.json"), "r") as f:
            loaded_data = json.load(f)
            loaded_modules = []
            for module in loaded_data:
                loaded_modules.append(Module(module["number"], module["name"], module["task_count"]))
            return loaded_modules
    except OSError:
        return []


def import_groups():
    try:
        with open(path.join(DATA_FILEPATH, "groups.json"), "r") as f:
            loaded_data = json.load(f)
            loaded_modules = []
            for group in loaded_data:
                loaded_modules.append(Group(group["number"], group["table"]))
            return loaded_modules
    except OSError:
        return []
