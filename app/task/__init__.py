import asyncio
from typing import Callable


def key(item):
    # If item is a tuple, use first element as the key for _set
    return item[0] if isinstance(item, tuple) else item


class TaskQueue(asyncio.Queue):
    def __init__(self, task: Callable, maxsize: int = 0) -> None:
        super().__init__(maxsize)
        self.task = task
        self._set = set()

    async def put(self, item):
        self._set.add(key(item))
        await super().put(item)

    def task_confirm(self, item):
        self.task_done()
        self._set.remove(key(item))

    def contains(self, item):
        return key(item) in self._set


async def worker_loop(*queues: TaskQueue):
    while True:
        for queue in queues:
            if not queue.empty():
                item = await queue.get()
                try:
                    await queue.task(item)
                finally:
                    queue.task_confirm(item)
                break
        else:
            await asyncio.sleep(1)
