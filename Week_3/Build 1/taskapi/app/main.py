from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import DATABASE_URL
from app.errors import InvalidTaskError, NotFoundError
from app.pg_repository import PostgresTaskRepository
from app.routes import build_router
from app.service import TaskService

# Stage 1 swap: this line used to be InMemoryTaskRepository()
repo = PostgresTaskRepository(DATABASE_URL)
# repo = InMemoryTaskRepository()  # For A2 fallback/testing

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


@app.get("/health")
async def health_check():
    # Simple health check - verify we can connect to the database and Redis
    health_status = {"status": "ok", "database": "ok", "redis": "ok"}

    # Check database
    try:
        with repo._conn() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        health_status["status"] = "error"
        health_status["database"] = "fail"
        health_status["database_error"] = str(e)

    # Check Redis (optional extra)
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        r.ping()
    except Exception as e:
        health_status["status"] = "error"
        health_status["redis"] = "fail"
        health_status["redis_error"] = str(e)

    if health_status["status"] == "error":
        return JSONResponse(status_code=503, content=health_status)
    return health_status