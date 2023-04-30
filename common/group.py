
class Group:
    def __init__(self, number: int, table: int):
        self.number = number  # e.g. Group 1
        self.table = table  # e.g. Table 5

    def __str__(self):
        return f"Group {self.number} table {self.table}"
