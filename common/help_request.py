from datetime import datetime
from enum import Enum
from uuid import uuid1


class RequestStatus(Enum):
    UNSENT: int = 0
    SENT: int = 1
    CONFIRMED: int = 2
    COMPLETED: int = 3


class HelpRequest:

    def __init__(self, group_number: int, module_number: int, task_idx: int, is_online: bool, zoom_url: str, comment: str):
        self.id = str(uuid1())
        self.module_number = module_number
        self.task_idx = task_idx
        self.is_online = is_online
        self.zoom_url = zoom_url
        self.comment = comment
        self.status = RequestStatus.UNSENT
        self.queue_pos = -1
        self.group_number = group_number
        self.claimed_by = None
        self.time = str(datetime.now().time())

    def payload(self):
        return str(vars(self))

