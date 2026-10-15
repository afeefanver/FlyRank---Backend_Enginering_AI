from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import InvalidTaskError, NotFoundError
from app.repository import InMemoryTaskRepository
from app.routes import build_router
from app.service import TaskService

# Before Stage 0, this is the only storage line:
repo = InMemoryTaskRepository()
# Stage 0 swap: this line used to be InMemoryTaskRepository()
# repo = SqliteTaskRepository()

service = TaskService(repo)

app = FastAPI(title="Task API")
app.include_router(build_router(service))


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"error": str(exc)})


@app.exception_handler(InvalidTaskError)
async def invalid_handler(request: Request, exc: InvalidTaskError):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request: title is required"})