import json

from common.help_request import HelpRequest

BROKER = "mqtt20.iik.ntnu.no"  # https://github.com/mqtt/mqtt.org/wiki/public_brokers
PORT = 1883

# topics
TOPIC_BASE = "ttm4115/team1/"
TOPIC_TA = TOPIC_BASE + "ta"
TOPIC_TASK = TOPIC_BASE + "task"
TOPIC_QUEUE = TOPIC_BASE + "queue"
TOPIC_SERVER = TOPIC_BASE + "server"

TYPE_ADD_HELP_REQUEST = 0
TYPE_CANCEL_HELP_REQUEST = 1


def parse_help_request(message: str) -> HelpRequest:
    data = json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))
    data["is_online"] = bool(data["is_online"])
    return HelpRequest(data["group_number"], data["module_number"], data["task_idx"], data["is_online"],
                       data["zoom_url"], data["comment"], data["id"])

class RequestWrapper:
    def __init__(self, request_type: int, data: str):
        self.request_type = request_type
        self.data = data

    def payload(self) -> str:
        return str(vars(self))
