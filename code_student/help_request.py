from enum import Enum


class RequestStatus(Enum):
    UNSENT: int = 0
    SENT: int = 1
    CONFIRMED: int = 2
    COMPLETED: int = 3


class HelpRequest:

    def __init__(self, module_number: int, task_idx: int, is_online: bool, zoom_url: str, comment: str):
        self.module_number = module_number
        self.task_idx = task_idx
        self.is_online = is_online
        self.zoom_url = zoom_url
        self.comment = comment
        self.status = RequestStatus.UNSENT
        self.queue_pos = -1

    def send_request(self):
        # TODO: send to some topic through MQTT
        self.status = RequestStatus.SENT

