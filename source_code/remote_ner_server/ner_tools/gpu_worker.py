from multiprocessing import Process

class GPUWorkerPool:

    def __init__(self, total_work: list[any], target_func, extra_param, gpu_count: int, worker_num_each_gpu: int):
        self.total_work = total_work
        self.target_func = target_func
        self.extra_param = extra_param
        self.gpu_count = gpu_count
        self.worker_num_each_gpu = worker_num_each_gpu
        self.worker_pool = []
        self.worker_per_gpu = worker_num_each_gpu
        self.base_task_count = len(self.total_work) // (self.gpu_count * self.worker_num_each_gpu)
        self.extra_tasks = len(self.total_work) % (self.gpu_count * self.worker_num_each_gpu)
        self.distribute_work()

    def distribute_work(self):
        start_index = 0
        worker_id = 0
        for gpu_id in range(self.gpu_count):
            for worker in range(self.worker_num_each_gpu):
                tasks_for_worker = self.base_task_count + (1 if worker_id < self.extra_tasks else 0)
                end_index = start_index + tasks_for_worker
                p = Process(target=self.target_func, args=(self.total_work[start_index:end_index], gpu_id, self.extra_param))
                self.worker_pool.append(p)
                print(f'GPU {gpu_id}, Worker {worker_id}: Processing tasks from index {start_index} to {end_index - 1} (Total tasks: {tasks_for_worker})')
                start_index = end_index
                worker_id += 1
        print(f'Total workers created: {len(self.worker_pool)}')

    def start_work(self):
        for p in self.worker_pool:
            p.start()
        for p in self.worker_pool:
            p.join()
