import math
from multiprocessing import Process

class WorkerPool:

    def __init__(self, worker_num, total_work: list[any], target_func, extra_param):
        self.worker_num = worker_num
        self.total_work = total_work
        self.target_func = target_func
        self.worker_pool = []
        self.extra_param = extra_param
        self.base_task_count = len(self.total_work) // self.worker_num
        self.extra_tasks = len(self.total_work) % self.worker_num
        start_index = 0
        for i in range(self.worker_num):
            tasks_for_worker = self.base_task_count + (1 if i < self.extra_tasks else 0)
            end_index = start_index + tasks_for_worker
            p = Process(target=self.target_func, args=(self.total_work[start_index:end_index], self.extra_param + [i]))
            self.worker_pool.append(p)
            print(f'Worker {i}: Processing tasks from index {start_index} to {end_index - 1} (Total tasks: {tasks_for_worker})')
            start_index = end_index
        print(f'Total workers created: {len(self.worker_pool)}')

    def start_work(self):
        for p in self.worker_pool:
            p.start()
        for p in self.worker_pool:
            p.join()
