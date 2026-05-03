from datetime import datetime

class ASBlock:

    def __init__(self, from_as_num: int, to_as_num: int, records_from_rir: str, changed_date: datetime, block_assigned_to: str):
        self.from_as_num = from_as_num
        self.to_as_num = to_as_num
        self.records_from_rir = records_from_rir
        self.changed_date = changed_date
        self.block_assigned_to = block_assigned_to

    def __repr__(self):
        return f'from_as_num: {self.from_as_num} \n to_as_num: {self.to_as_num} \n records_from_rir: {self.records_from_rir} \n changed_date: {self.changed_date} \n block_assigned_to: {self.block_assigned_to}'
