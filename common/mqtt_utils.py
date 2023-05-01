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


class RequestWrapper:
    def __init__(self, request_type: int, data: str):
        self.request_type = request_type
        self.data = data

    def payload(self) -> str:
        return str(vars(self))
