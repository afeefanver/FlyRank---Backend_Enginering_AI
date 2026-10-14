from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Task API", description="A small REST API that manages a to-do list")

# In-memory storage for tasks
tasks = []
next_id = 1

class TaskBase(BaseModel):
    title: str
    done: bool = False

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

@app.get("/")
def read_root():
    return {
        "message": "Task API - My First CRUD API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    return tasks

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    for task in tasks:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate):
    global next_id
    # Validation: title must be present and non-empty string (whitespace-only rejected)
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title must be present and a non-empty string")

    new_task = Task(id=next_id, title=task.title.strip(), done=task.done)
    tasks.append(new_task)
    next_id += 1
    return new_task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskUpdate):
    # Validation: if title is provided, it must be present and non-empty string
    if task_update.title is not None and (not task_update.title or not task_update.title.strip()):
        raise HTTPException(status_code=400, detail="Title must be present and a non-empty string")

    for task in tasks:
        if task.id == task_id:
            if task_update.title is not None:
                task.title = task_update.title.strip()
            if task_update.done is not None:
                task.done = task_update.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    global tasks
    for i, task in enumerate(tasks):
        if task.id == task_id:
            tasks.pop(i)
            return None
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")