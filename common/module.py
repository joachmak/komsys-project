from common.help_request import HelpRequest


class Module:
    def __init__(self, number: int, name: str, task_count: int):
        self.number = number  # e.g. module 1
        self.name = name  # e.g. "Sequence diagrams"
        self.task_count = task_count
        self.finished_tasks = [False] * task_count  # finished-status for each task
        self.requests = []
        self.latest_request = None  # for easy access

    def set_finish_status(self, task_idx: int, status: bool):
        """ Set the finis-status of a task """
        if task_idx >= len(self.finished_tasks):
            print("Cannot update task status, index out of bounds")
            return
        self.finished_tasks[task_idx] = status

    def add_request(self, request: HelpRequest):
        self.requests.append(request)
        self.latest_request = request

    def __str__(self):
        return f"Module {self.number}: {self.name}, {self.task_count} tasks"
