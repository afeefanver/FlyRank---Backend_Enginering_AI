from fastapi import APIRouter, Response
from app.schemas import TaskIn
from app.service import TaskService


def build_router(service: TaskService) -> APIRouter:
    router = APIRouter()

    @router.get("/tasks")
    def list_tasks():
        return service.list_tasks()

    @router.get("/tasks/{task_id}")
    def get_task(task_id: int):
        return service.get_task(task_id)

    @router.post("/tasks", status_code=201)
    def create_task(body: TaskIn):
        return service.create_task(body.title, body.done)

    @router.put("/tasks/{task_id}")
    def update_task(task_id: int, body: TaskIn):
        return service.update_task(task_id, body.title, body.done)

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int):
        service.delete_task(task_id)
        return Response(status_code=204)

    return router