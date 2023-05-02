import json

from common.feedback import Feedback
from common.help_request import HelpRequest

BROKER = "mqtt20.iik.ntnu.no"  # https://github.com/mqtt/mqtt.org/wiki/public_brokers
PORT = 1883

# topics
TOPIC_BASE = "ttm4115/team1/"
TOPIC_TA = TOPIC_BASE + "ta"
TOPIC_TASK = TOPIC_BASE + "task"
TOPIC_QUEUE = TOPIC_BASE + "queue"
TOPIC_SERVER = TOPIC_BASE + "server"

# From student
TYPE_ADD_HELP_REQUEST = 0
TYPE_CANCEL_HELP_REQUEST = 1
TYPE_SEND_FEEDBACK = 2
TYPE_CONFIRM_CLAIM = 4

# From TA
TYPE_CLAIM_REQUEST = 3
TYPE_RESOLVE_REQUEST = 5


def parse_help_request(message: str) -> HelpRequest:
    """
    :param message: message to parse
    :return: help request object with data contained in message
    """
    data = json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))
    data["is_online"] = bool(data["is_online"])
    return HelpRequest(data["group_number"], data["module_number"], data["task_idx"], data["is_online"],
                       data["zoom_url"], data["comment"], data["id"])

def parse_cancel_request(message: str) -> str:
    """ Returns id of request to cancel """
    return json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))["id"]


def parse_feedback(message: str) -> Feedback:
    data = json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))
    return Feedback(data["group_number"], data["module_number"], data["task_number"], data["comment"], data["difficulty"])


def parse_claim_request(message: str) -> (str, str):
    """ Return (request_id, ta_name) """
    data = json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))
    return data["id"], data["ta"]


def parse_resolve_request(message: str) -> str:
    """ Returns id of request to resolve. """
    return json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))["id"]


def parse_confirm_claim(message: str) -> str:
    """ Return ta_name """
    data = json.loads(str(message.split("\"")[1].replace("'", "\"").strip()))
    return data["ta"]


def get_request_type(message: str) -> int:
    return int(json.loads(str(message.split("\"")[0].replace("'", "\"").strip().split(",")[0])[2:] + "}")['request_type'])


class RequestWrapper:
    def __init__(self, request_type: int, data: str):
        self.request_type = request_type
        self.data = data

    def payload(self) -> str:
        return str(vars(self))
