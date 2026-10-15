from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class TaskRepository(ABC):
    @abstractmethod
    def list_all(self) -> List[Dict]:
        ...

    @abstractmethod
    def get(self, task_id: int) -> Optional[Dict]:
        ...

    @abstractmethod
    def create(self, title: str, done: bool) -> Dict:
        ...

    @abstractmethod
    def update(self, task_id: int, title: str, done: bool) -> Optional[Dict]:
        ...

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        ...


class InMemoryTaskRepository(TaskRepository):
    def __init__(self):
        self._tasks: Dict[int, Dict] = {}
        self._next_id = 1

    def list_all(self) -> List[Dict]:
        return list(self._tasks.values())

    def get(self, task_id: int) -> Optional[Dict]:
        return self._tasks.get(task_id)

    def create(self, title: str, done: bool) -> Dict:
        task = {"id": self._next_id, "title": title, "done": done}
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    def update(self, task_id: int, title: str, done: bool) -> Optional[Dict]:
        if task_id not in self._tasks:
            return None
        self._tasks[task_id] = {"id": task_id, "title": title, "done": done}
        return self._tasks[task_id]

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None