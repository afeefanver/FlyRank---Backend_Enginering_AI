from app.errors import InvalidTaskError, NotFoundError
from app.repository import TaskRepository


class TaskService:
    def __init__(self, repo: TaskRepository):
        self.repo = repo

    @staticmethod
    def _validate(title: str):
        if not title or not title.strip():
            raise InvalidTaskError("title is required")

    def list_tasks(self):
        return self.repo.list_all()

    def get_task(self, task_id: int):
        task = self.repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    def create_task(self, title: str, done: bool):
        self._validate(title)
        return self.repo.create(title.strip(), done)

    def update_task(self, task_id: int, title: str, done: bool):
        self._validate(title)
        task = self.repo.update(task_id, title.strip(), done)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    def delete_task(self, task_id: int):
        if not self.repo.delete(task_id):
            raise NotFoundError("Task not found")