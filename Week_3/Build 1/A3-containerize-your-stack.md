# A3: Containerize Your Stack

Run your task API against Postgres in Docker, and start app + database with one command.

**Assumptions in this guide (change them if they're wrong):**

- Python lane, FastAPI, and the `psycopg` driver.
- Your A2 code is already layered: routes → service → repository, with a repository interface and an in-memory implementation.
- The API listens on port **3000**.

If you used Node, or your A2 layout differs, keep the stages and the infrastructure files (Dockerfile, compose, `.env`) as they are, and adapt only the repository code.

---

## Target layout

```
taskapi/
├── app/
│   ├── __init__.py
│   ├── main.py            # wires everything together (the one-line swap lives here)
│   ├── config.py
│   ├── schemas.py
│   ├── errors.py
│   ├── repository.py      # interface + in-memory (your existing A2 code)
│   ├── pg_repository.py   # NEW: Postgres repository
│   ├── service.py         # unchanged from A2
│   └── routes.py          # unchanged from A2
├── db/
│   └── init.sql           # NEW: table definition
├── Dockerfile             # NEW
├── compose.yaml           # NEW
├── .env                   # NEW, git-ignored
├── .env.example           # NEW, committed
├── .dockerignore          # NEW
├── .gitignore
├── requirements.txt
└── README.md
```

Only the files marked NEW should be new. If you find yourself editing `service.py` or `routes.py`, stop. The point of A2's layering is that they don't change.

---

## Stage 0: Postgres in Docker

```bash
docker --version

docker run --name taskdb \
  -e POSTGRES_PASSWORD=change_me \
  -e POSTGRES_DB=tasks \
  -p 5432:5432 \
  -v taskdata:/var/lib/postgresql/data \
  -d postgres:16

docker ps
docker exec -it taskdb psql -U postgres -d tasks
```

Inside `psql`, type `\dt` (no tables yet), then `\q`.

Create `.gitignore` **before your first commit**:

```
.env
.venv/
venv/
__pycache__/
*.pyc
node_modules/
```

**Checkpoint:** `docker ps` shows a running postgres container and `psql` opens.

```bash
git add . && git commit -m "Stage 0: Postgres in Docker + gitignore"
```

---

## Stage 1: Connect with a secret, create the table, seed once

### `.env` (git-ignored)

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change_me
POSTGRES_DB=tasks
DATABASE_URL=postgres://postgres:change_me@localhost:5432/tasks
```

### `.env.example` (committed, placeholders only)

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace_with_a_password
POSTGRES_DB=tasks
DATABASE_URL=postgres://postgres:replace_with_a_password@localhost:5432/tasks
```

Use a simple password (letters and numbers). Special characters need URL-encoding inside `DATABASE_URL`.

### `requirements.txt`

```
fastapi
uvicorn[standard]
psycopg[binary]
python-dotenv
```

```bash
pip install -r requirements.txt
```

### `db/init.sql`

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);
```

### `app/config.py`

```python
import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
```

### `app/schemas.py`

```python
from pydantic import BaseModel


class TaskIn(BaseModel):
    title: str
    done: bool = False
```

### `app/errors.py`

```python
class NotFoundError(Exception):
    pass


class InvalidTaskError(Exception):
    pass
```

### `app/repository.py` (the interface, plus your existing in-memory version)

Keep whatever you already wrote in A2. It must look like this to the rest of the app:

```python
from abc import ABC, abstractmethod


class TaskRepository(ABC):
    @abstractmethod
    def list_all(self) -> list[dict]: ...

    @abstractmethod
    def get(self, task_id: int) -> dict | None: ...

    @abstractmethod
    def create(self, title: str, done: bool) -> dict: ...

    @abstractmethod
    def update(self, task_id: int, title: str, done: bool) -> dict | None: ...

    @abstractmethod
    def delete(self, task_id: int) -> bool: ...


class InMemoryTaskRepository(TaskRepository):
    def __init__(self):
        self._tasks: dict[int, dict] = {}
        self._next_id = 1

    def list_all(self):
        return list(self._tasks.values())

    def get(self, task_id):
        return self._tasks.get(task_id)

    def create(self, title, done):
        task = {"id": self._next_id, "title": title, "done": done}
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    def update(self, task_id, title, done):
        if task_id not in self._tasks:
            return None
        self._tasks[task_id] = {"id": task_id, "title": title, "done": done}
        return self._tasks[task_id]

    def delete(self, task_id):
        return self._tasks.pop(task_id, None) is not None
```

### `app/pg_repository.py` (every database line lives here)

```python
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.repository import TaskRepository

INIT_SQL = Path(__file__).resolve().parent.parent / "db" / "init.sql"

SEED_TASKS = [
    ("Learn Docker", False),
    ("Connect the API to Postgres", False),
    ("Prove the data survives a restart", False),
]

COLUMNS = "id, title, done"


class PostgresTaskRepository(TaskRepository):
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._wait_for_db()
        self._init_schema()

    def _conn(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _wait_for_db(self, attempts: int = 15, delay: float = 2.0):
        for attempt in range(attempts):
            try:
                with self._conn():
                    return
            except psycopg.OperationalError:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay)

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute(INIT_SQL.read_text())
            count = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"]
            if count == 0:
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS
                    )

    def list_all(self):
        with self._conn() as conn:
            return conn.execute(f"SELECT {COLUMNS} FROM tasks ORDER BY id").fetchall()

    def get(self, task_id):
        with self._conn() as conn:
            return conn.execute(
                f"SELECT {COLUMNS} FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()

    def create(self, title, done):
        with self._conn() as conn:
            return conn.execute(
                f"INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING {COLUMNS}",
                (title, done),
            ).fetchone()

    def update(self, task_id, title, done):
        with self._conn() as conn:
            return conn.execute(
                f"UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING {COLUMNS}",
                (title, done, task_id),
            ).fetchone()

    def delete(self, task_id):
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0
```

Every query passes values as a separate tuple (`%s` placeholders). Never build SQL with f-strings around user input. The only f-string above is the fixed column list, which contains no user data.

### `app/service.py` (if you don't already have one)

```python
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
```

### `app/routes.py` (if you don't already have one)

```python
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
```

### `app/main.py` (the one place the swap happens)

```python
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
```

Add an empty `app/__init__.py`.

### Run it

```bash
uvicorn app.main:app --port 3000 --reload
```

**Checkpoint:**

```bash
docker exec -it taskdb psql -U postgres -d tasks -c "\dt"
docker exec -it taskdb psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

You see the `tasks` table and three rows. Restart the app three times. There are still exactly three rows.

```bash
git add . && git commit -m "Stage 1: connect via .env and create table"
```

---

## Stage 2: Read from Postgres

```bash
curl -i http://localhost:3000/tasks
curl -i http://localhost:3000/tasks/1
curl -i http://localhost:3000/tasks/999
```

**Checkpoint:** the first two return `200` with rows from Postgres. The third returns `404` with `{"error":"Task not found"}`.

```bash
git add . && git commit -m "Stage 2: read from Postgres"
```

---

## Stage 3: Create, update, delete

```bash
# create -> 201
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Write the README","done":false}'

# empty title -> 400
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":""}'

# update -> 200
curl -i -X PUT http://localhost:3000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"title":"Write the README","done":true}'

# delete -> 204, then 404
curl -i -X DELETE http://localhost:3000/tasks/4
curl -i http://localhost:3000/tasks/4
```

**Checkpoint:** you see `201`, `400`, `200`, `204`, `404`, confirming each step with `GET /tasks`.

```bash
git add . && git commit -m "Stage 3: full CRUD on Postgres"
```

---

## Stage 4: One command for the whole stack

### `Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY db ./db
EXPOSE 3000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
```

### `.dockerignore`

```
.env
.git
.venv
venv
__pycache__
*.pyc
```

### `compose.yaml`

Compose reads `.env` automatically, so no password is written in this file.

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - taskdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 3s
      timeout: 3s
      retries: 10

  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      # inside the compose network the host is the service name "db", not localhost
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy

volumes:
  taskdata:
```

### Run it

```bash
docker stop taskdb && docker rm taskdb   # free port 5432
docker compose up --build
```

**Persistence proof (this goes in your README):**

```bash
# 1. create a few tasks
curl -s -X POST localhost:3000/tasks -H "Content-Type: application/json" -d '{"title":"survive a restart"}'

# 2. stop everything (keeps the volume) and start again
docker compose down
docker compose up -d

# 3. the tasks are still there
curl -s localhost:3000/tasks
```

Use `docker compose down -v` only when you want to delete the data on purpose. The `-v` removes the volume.

**Checkpoint:** from a clean state, `docker compose up` starts both services, and your tasks are still there after `down` then `up`.

```bash
git add . && git commit -m "Stage 4: docker-compose the whole stack"
```

---

## Stage 5: Publish to GitHub and write the README

1. Run `git status` and `git log --stat` to confirm `.env` is not tracked and never appeared in history. If it did, rotate the password and rewrite history before pushing.
2. Push to your public repo.
3. Clone it fresh in another folder and test:

```bash
git clone <your-repo-url> fresh && cd fresh
cp .env.example .env      # then edit the password
docker compose up --build
curl -i localhost:3000/tasks
```

4. Take a screenshot of your data in the database: `psql` with `\dt` and `SELECT * FROM tasks;`, or DBeaver / pgAdmin / TablePlus.

### README template

````markdown
# Task API on Postgres

A task CRUD API (FastAPI) storing data in PostgreSQL, started with one command.
Storage has moved from memory (A1) to SQLite (A2) to containerized Postgres (A3).

## Run it

```bash
cp .env.example .env     # set a password
docker compose up --build
```

API: http://localhost:3000

## Environment variables

See `.env.example`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`.
`.env` is git-ignored. Never commit it.

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /tasks | 200 | n/a |
| GET | /tasks/{id} | 200 | 404 |
| POST | /tasks | 201 | 400 |
| PUT | /tasks/{id} | 200 | 400, 404 |
| DELETE | /tasks/{id} | 204 | 404 |

## Example

```
<paste one curl -i output here>
```

## Data in the database

<screenshot of psql \dt and SELECT * FROM tasks;>

## What changed in this assignment

I replaced the in-memory repository with `PostgresTaskRepository`, which implements the same
`TaskRepository` interface. `service.py` and `routes.py` were **not changed**. The only edit
outside the new repository and infrastructure files was one line in `main.py` that constructs
the repository. [Say honestly if you had to touch anything else, and why.]

## How I proved persistence

1. Created tasks with POST /tasks.
2. Ran `docker compose down` then `docker compose up`.
3. `GET /tasks` returned the same rows, because the named volume `taskdata` kept the data.
````

**Checkpoint:** on a clean clone, `cp .env.example .env && docker compose up` starts the stack and `GET /tasks` returns the seeded tasks in under 5 minutes.

```bash
git add . && git commit -m "Stage 5: one-command stack + docs"
git push
```

That gives you six commits, one per stage.

---

## Optional extras

### Index and `EXPLAIN ANALYZE`

```sql
-- seed some rows
INSERT INTO tasks (title, done)
SELECT 'task ' || g, g % 2 = 0 FROM generate_series(1, 200000) g;

EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = true AND title = 'task 100000';

CREATE INDEX idx_tasks_title ON tasks (title);

EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = true AND title = 'task 100000';
```

Paste both outputs in the README and say in one line what changed (a sequential scan became an index scan, and the time dropped).

### Redis in compose

```yaml
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

Then `pip install redis`, and on startup call `redis.Redis(host="redis").ping()`.

### Health check

```python
@app.get("/health")
def health():
    repo.list_all()   # or run SELECT 1 inside the repository
    return {"status": "ok", "db": "ok"}
```

A load balancer calls this to decide whether to send traffic to an instance. If the database check fails, the instance is taken out of rotation.

---

## Stage 6: The AI rematch (bonus)

1. Write your own prompt asking an AI to containerize a task CRUD API onto Postgres, without copying from this guide. Specify: your lane and driver, the `tasks` table and seed-once rule, the five endpoints with identical behavior, parameterized queries, the password from `.env`, a volume, and one-command startup.
2. Put the AI's output in `ai-version/` (or a branch). Your hand-built stack stays untouched.
3. Run it. Does `docker compose up` work first try? Do the tasks survive `down` then `up`? Is the password hardcoded?
4. Diff it with yours: `git diff --no-index . ai-version`.
5. Add an "AI vs me" section to the README with your full prompt and at least three concrete differences:
   - What did it do better?
   - What did it get wrong or ignore?
   - What did your prompt forget to specify?
6. Rewrite your prompt once, regenerate, and note in one sentence what changed.

Commit: `Stage 6: AI vs me`

---

## Final checklist

- [ ] Postgres runs in Docker with a volume, and `docker compose up` starts the whole stack
- [ ] Connection string comes from `.env` (git-ignored), and `.env.example` is committed
- [ ] No credentials are hardcoded anywhere, including `compose.yaml`
- [ ] Table is created automatically and seeded with three tasks only on the first run
- [ ] All five endpoints work with parameterized queries and correct status codes (200, 201, 204, 400, 404)
- [ ] Postgres repository replaced the in-memory one, with service and routes unchanged (stated honestly in the README)
- [ ] Persistence proven across `docker compose down` and `up`, and the method is in the README
- [ ] Public repo has the README, an endpoint table, a `curl -i` output, and a database screenshot
- [ ] `git log` shows one commit per stage, and `.env` appears nowhere in history

## Troubleshooting

| Problem | Fix |
|---|---|
| `port is already allocated` on 5432 | Run `docker stop taskdb && docker rm taskdb`, or stop any local Postgres. |
| API can't connect inside compose | The host must be `db`, not `localhost`. Check the `DATABASE_URL` in `compose.yaml`. |
| `password authentication failed` | The volume remembers the old password. Run `docker compose down -v` once, then `up`. |
| API starts before the database is ready | The `healthcheck` and `depends_on: condition: service_healthy` handle this. Keep both. |
| Tasks vanish after `down` | You used `down -v`, or the volume isn't mounted at `/var/lib/postgresql/data`. |
| `.env` was committed | Rotate the password now, then remove it from history (`git filter-repo` or recreate the repo). |
