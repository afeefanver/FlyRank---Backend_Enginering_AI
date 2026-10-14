from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# In-memory storage
tasks = []
task_id_counter = 1

class Task(BaseModel):
    id: int
    title: str
    done: bool = False

class TaskCreate(BaseModel):
    title: str
    done: Optional[bool] = False

@app.get("/")
def root():
    return {"message": "Task API"}

@app.get("/health")
def health():
    return {"status": "OK"}

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    return tasks

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    for task in tasks:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate):
    global task_id_counter
    if not task.title:
        raise HTTPException(status_code=422, detail="Title is required")

    new_task = Task(id=task_id_counter, title=task.title, done=task.done)
    tasks.append(new_task)
    task_id_counter += 1
    return new_task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskCreate):
    for task in tasks:
        if task.id == task_id:
            if not task_update.title:
                raise HTTPException(status_code=422, detail="Title is required")
            task.title = task_update.title
            task.done = task_update.done
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    global tasks
    tasks = [task for task in tasks if task.id != task_id]
    return {"message": "Task deleted"}