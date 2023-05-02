import datetime
from typing import Optional


def is_in_(l: list, req_id: str):
    for entry in l:
        if req_id == entry[0]:
            return True
    return False


def remove_from_(l: list, req_id: str):
    for i in range(len(l)):
        elem = l[i]
        if elem[0] == req_id:
            l.pop(i)
            break


def get_request_time_from_(l: list, req_id: str) -> Optional[datetime.datetime]:
    for elem in l:
        if elem[0] == req_id:
            return elem[1]
    return None


class QueueManager:

    def __init__(self):
        self.local_q_pos = None
        self.global_q_pos = 0
        # list of tuple(id, time)
        self.req_list = []
        # tuple (id, time)
        self.active_request = None

    def print_queue_positions(self):
        print(f"Local: {self.local_q_pos}, Global: {self.global_q_pos}")

    def on_cancel(self, req_id: str):
        is_mine = self.active_request is not None and self.active_request[0] == req_id
        if is_in_(self.req_list, req_id):
            req_time = get_request_time_from_(self.req_list, req_id)
            # remove from a_list
            remove_from_(self.req_list, req_id)
            self.global_q_pos -= 1
            # determine how to adjust local queue:
            if is_mine:
                self.local_q_pos = None
                self.active_request = None
            elif self.active_request is not None and req_time is not None and req_time < self.active_request[1]:
                # you have an active request and a request before it was canceled
                self.local_q_pos -= 1

    def on_resolve(self, req_id: str):
        self.on_cancel(req_id)

    def on_add(self, req_id: str, time: datetime.datetime, is_mine: bool):
        if is_in_(self.req_list, req_id):
            return
        self.req_list.append((req_id, time))
        self.global_q_pos += 1
        if is_mine:
            self.local_q_pos = self.global_q_pos
            self.active_request = (req_id, time)


if __name__ == "__main__":
    # ==== TEST QUEUE MANAGER ====

    reqA = "A"
    reqB = "B"
    reqC = "C"  # <-- mine
    reqD = "D"

    qm = QueueManager()

    qm.on_add(reqA, datetime.datetime.now(), False)
    qm.print_queue_positions()
    qm.on_add(reqB, datetime.datetime.now(), False)
    qm.print_queue_positions()
    qm.on_add(reqC, datetime.datetime.now(), True)
    qm.print_queue_positions()
    qm.on_add(reqD, datetime.datetime.now(), False)
    qm.print_queue_positions()
    print("\n")
    qm.on_resolve(reqA)
    qm.print_queue_positions()
    qm.on_resolve(reqC)
    qm.print_queue_positions()
    qm.on_resolve(reqB)
    qm.print_queue_positions()
    print("\n")
    qm.on_add(reqC, datetime.datetime.now(), True)
    qm.print_queue_positions()
