# A2: Connecting Your CRUD to the Database (SQLite)

Move your task API's storage from memory to a SQLite file (`tasks.db`). The endpoints behave exactly as before, but the data now survives a restart.

**Assumptions in this guide (change them if they're wrong):**

- Python lane, FastAPI, and the built-in `sqlite3` module (nothing extra to install for the database).
- Port **3000**, with the same five endpoints and status codes as A1.
- The code is split into routes → service → repository. That way this assignment changes one file, and A3 (Postgres) will change only one file again.

If you used Node, keep the stages and swap in `better-sqlite3` for the repository file. If your A1 already has its own structure, keep it. Only the storage code should change.

---

## Target layout

```
taskapi/
├── app/
│   ├── __init__.py
│   ├── main.py               # wires everything together (the one-line swap lives here)
│   ├── schemas.py
│   ├── errors.py
│   ├── repository.py         # interface + in-memory (your A1 storage)
│   ├── sqlite_repository.py  # NEW: SQLite repository
│   ├── service.py
│   └── routes.py
├── tests/
│   └── smoke.sh              # the same curl checks, run against either storage
├── .gitignore
├── requirements.txt
└── README.md
```

`tasks.db` is created automatically the first time the app runs. It is git-ignored, so every clone starts with a fresh database.

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install fastapi "uvicorn[standard]"
pip freeze > requirements.txt    # or write it by hand: fastapi, uvicorn[standard]
```

`.gitignore`:

```
.venv/
venv/
__pycache__/
*.pyc
tasks.db
.env
```

Install **DB Browser for SQLite** (free, sqlitebrowser.org) now. You'll need it in Stage 4.

---

## The shared files (same shape as A1)

If your A1 already has equivalents, keep yours. They must expose the same behavior.

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

### `app/repository.py`

The interface is the contract. The in-memory version is your A1 storage, and you keep it. It is what makes the swap provable.

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

### `app/service.py`

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

### `app/routes.py`

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

### `app/main.py`

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import InvalidTaskError, NotFoundError
from app.repository import InMemoryTaskRepository
from app.routes import build_router
from app.service import TaskService

# Before Stage 0, this is the only storage line:
repo = InMemoryTaskRepository()

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

### `tests/smoke.sh` (your proof that the API didn't change)

```bash
#!/usr/bin/env bash
# Usage: bash tests/smoke.sh   (server must be running on port 3000)
BASE=http://localhost:3000
check() { # name expected_status actual_status
  if [ "$2" = "$3" ]; then echo "PASS $1 ($3)"; else echo "FAIL $1 (expected $2, got $3)"; fi
}

code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

check "list tasks"      200 "$(code $BASE/tasks)"
check "unknown id"      404 "$(code $BASE/tasks/99999)"
check "empty title"     400 "$(code -X POST $BASE/tasks -H 'Content-Type: application/json' -d '{"title":""}')"
check "create"          201 "$(code -X POST $BASE/tasks -H 'Content-Type: application/json' -d '{"title":"smoke test"}')"

ID=$(curl -s $BASE/tasks | python3 -c "import sys,json; print(max(t['id'] for t in json.load(sys.stdin)))")
check "update"          200 "$(code -X PUT $BASE/tasks/$ID -H 'Content-Type: application/json' -d '{"title":"smoke test","done":true}')"
check "delete"          204 "$(code -X DELETE $BASE/tasks/$ID)"
check "delete again"    404 "$(code -X DELETE $BASE/tasks/$ID)"
```

Run it once against the in-memory version **before you start Stage 0**. You'll run it again after the swap.

```bash
uvicorn app.main:app --port 3000 --reload
bash tests/smoke.sh
```

---

## Stage 0: Create your database

Create `app/sqlite_repository.py`. Write the connection helper, the table, and the seed first. You'll fill in the other methods in the following stages (or paste all of it now and commit stage by stage).

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.repository import TaskRepository

DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"

SEED_TASKS = [
    ("Learn SQLite", 0),
    ("Move storage to the database", 0),
    ("Prove the data survives a restart", 0),
]

COLUMNS = "id, title, done"


def _to_task(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


class SqliteTaskRepository(TaskRepository):
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = str(db_path)
        self._init_schema()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:  # commits on success, rolls back on error
                yield conn
        finally:
            conn.close()

    def _init_schema(self):
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done  INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            if count == 0:
                # same connection = same transaction: all three seeds or none
                conn.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS
                )

    # --- Stage 1: read ---------------------------------------------------
    def list_all(self):
        with self._connection() as conn:
            rows = conn.execute(f"SELECT {COLUMNS} FROM tasks ORDER BY id").fetchall()
            return [_to_task(r) for r in rows]

    def get(self, task_id):
        with self._connection() as conn:
            row = conn.execute(
                f"SELECT {COLUMNS} FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return _to_task(row) if row else None

    # --- Stage 2: create -------------------------------------------------
    def create(self, title, done):
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (?, ?)", (title, int(done))
            )
            row = conn.execute(
                f"SELECT {COLUMNS} FROM tasks WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return _to_task(row)

    # --- Stage 3: update and delete -------------------------------------
    def update(self, task_id, title, done):
        with self._connection() as conn:
            cur = conn.execute(
                "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
                (title, int(done), task_id),
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                f"SELECT {COLUMNS} FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return _to_task(row)

    def delete(self, task_id):
        with self._connection() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0
```

Every query passes values as a separate tuple with `?` placeholders. The only f-string is the fixed column list, which contains no user data.

Now do the one-line swap in `app/main.py`:

```python
from app.sqlite_repository import SqliteTaskRepository

# Stage 0 swap: this line used to be InMemoryTaskRepository()
repo = SqliteTaskRepository()
```

Run it:

```bash
uvicorn app.main:app --port 3000 --reload
```

**Checkpoint:** restart the app three times. `curl localhost:3000/tasks` shows **exactly three** tasks, not six or nine. A `tasks.db` file now exists in your project folder.

```bash
git add . && git commit -m "Stage 0: create SQLite database"
```

---

## Stage 1: Read from the database

```bash
curl -i http://localhost:3000/tasks
curl -i http://localhost:3000/tasks/1
curl -i http://localhost:3000/tasks/999
```

**Checkpoint:** the first two return `200` with rows read live from `tasks.db`. The third returns `404` with `{"error":"Task not found"}`.

```bash
git add . && git commit -m "Stage 1: database read endpoints"
```

---

## Stage 2: Create new tasks

```bash
curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'

curl -i -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":""}'
```

The first returns `201` with the new task and the id the database gave it. The second returns `400`.

**Checkpoint:** create two tasks, **stop the server (Ctrl+C), start it again**, then run `curl localhost:3000/tasks`. Your tasks are still there. This is the first time your data has survived a restart.

```bash
git add . && git commit -m "Stage 2: insert into database"
```

---

## Stage 3: Update and delete

```bash
# update -> 200
curl -i -X PUT http://localhost:3000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk","done":true}'

# delete -> 204, then 404
curl -i -X DELETE http://localhost:3000/tasks/4
curl -i http://localhost:3000/tasks/4

# unknown id -> 404
curl -i -X PUT http://localhost:3000/tasks/999 \
  -H "Content-Type: application/json" \
  -d '{"title":"x","done":false}'
```

**Checkpoint:** create a task, mark it done with `PUT`, then `DELETE` it, confirming each step with `GET /tasks`. Restart the server between two steps and watch the state hold. You see `201`, `200`, `204` and `404`. Then run `bash tests/smoke.sh` and check that all lines say `PASS`.

```bash
git add . && git commit -m "Stage 3: update and delete with SQL"
```

---

## Stage 4: Learn your first SQL by hand

1. Open `tasks.db` in DB Browser for SQLite (File → Open Database). Browse the `tasks` table. It is the same data your API serves.
2. Go to the **Execute SQL** tab and run each query below, one at a time:

```sql
SELECT * FROM tasks;                  -- list every task
SELECT * FROM tasks WHERE done = 1;   -- only completed tasks
SELECT COUNT(*) FROM tasks;           -- how many tasks are there?
UPDATE tasks SET done = 1;            -- mark every task completed
DELETE FROM tasks WHERE done = 1;     -- delete all completed tasks
```

3. After each query that changes data, click **Write Changes** (Ctrl+S) in DB Browser, then run `curl localhost:3000/tasks`. Your API reflects the change instantly, with no restart, because both read the same file.

Be careful with `UPDATE` and `DELETE`: without a `WHERE` they change every row.

**Checkpoint:** you changed the database by hand and saw that change through your API. Save one query and one sentence on what it returned, for your README.

```bash
git add . && git commit -m "Stage 4: explored SQLite"
```

---

## Stage 5: Publish and document

1. Make sure `tasks.db` is in `.gitignore` and not tracked: `git ls-files | grep tasks.db` should print nothing.
2. Test a clean start. Stop the server, delete `tasks.db`, start again, and `GET /tasks` shows the three seeded tasks.
3. Take a screenshot of your database open in DB Browser.
4. Write the README (template below), then push.

### README template

````markdown
# Task API on SQLite

A task CRUD API (FastAPI) that stores its data in a SQLite file, `tasks.db`.
Storage has moved from memory (A1) to SQLite (A2).

## Why SQLite

It's a single file with no server to install, the database is created automatically on
first run, and the data survives restarts. That's exactly what this project needs.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 3000
```

`tasks.db` is created automatically with its `tasks` table and three seeded tasks.
It is git-ignored, so every clone starts fresh.

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /tasks | 200 | n/a |
| GET | /tasks/{id} | 200 | 404 |
| POST | /tasks | 201 | 400 |
| PUT | /tasks/{id} | 200 | 400, 404 |
| DELETE | /tasks/{id} | 204 | 404 |

## Persistence

I created tasks, stopped the server, started it again, and `GET /tasks` returned the same
rows. I also opened `tasks.db` in DB Browser and saw the same data.

<screenshot of DB Browser showing the tasks table>

## A SQL query I ran by hand

```sql
SELECT COUNT(*) FROM tasks;
```

It returned [the number you saw]. [One sentence on what it told you.]

## The API didn't change

`tests/smoke.sh` passes against the in-memory version and against SQLite. Identical tests
passing against both is the proof that storage is an implementation detail: the routes and
the service never knew the storage changed. Only `sqlite_repository.py` is new, and `main.py`
changed by one line. [Say honestly if you had to touch anything else, and why.]
````

**Checkpoint:** on a clean clone, one documented command starts the server, `tasks.db` is created automatically, and `GET /tasks` returns three tasks. A stranger can do this in under 5 minutes.

```bash
git add . && git commit -m "Stage 5: database documentation"
git push
```

---

## Optional extras

### Search, filter, sort (let SQL do the work)

Add optional filters to the repository and route. This extends the interface, so add the same parameters to `TaskRepository.list_all` and the in-memory version, or the swap proof will break.

In `sqlite_repository.py`:

```python
def list_all(self, search: str | None = None, done: bool | None = None):
    sql = f"SELECT {COLUMNS} FROM tasks"
    clauses, params = [], []
    if search:
        clauses.append("title LIKE ?")
        params.append(f"%{search}%")
    if done is not None:
        clauses.append("done = ?")
        params.append(int(done))
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY title"
    with self._connection() as conn:
        return [_to_task(r) for r in conn.execute(sql, params).fetchall()]
```

The `?` placeholders still carry every user value. Only fixed text is joined into the SQL string.

In `routes.py`:

```python
@router.get("/tasks")
def list_tasks(search: str | None = None, done: bool | None = None):
    return service.list_tasks(search, done)
```

Then update `TaskService.list_tasks(self, search=None, done=None)` to pass them through. Try `GET /tasks?search=milk` and `GET /tasks?done=true`.

### Stats

```python
def stats(self):
    with self._connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
        return {"total": total, "done": done, "open": total - done}
```

### Index (and what it's for)

```sql
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks (done);
```

An index is a sorted lookup structure that lets the database find matching rows without scanning the whole table. Compare `EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE done = 1;` before and after.

### Transaction

The seed insert in `_init_schema` already runs inside one transaction, because it uses a single connection with `with conn:`. That makes it all-or-nothing: if the second insert failed, the first would roll back, and you wouldn't end up with a half-seeded table. Say that in one line in your README.

### Timestamps

Add `created_at TEXT DEFAULT CURRENT_TIMESTAMP` to the table. `CREATE TABLE IF NOT EXISTS` won't alter an existing table, so you'll have to delete `tasks.db` or run an `ALTER TABLE`. Write two sentences in your README about how that felt. That feeling is why migrations exist.

```bash
git commit -am "Extras: <what you added>"
```

---

## Stage 6: The AI rematch (bonus)

1. Write your own prompt asking an AI to move an in-memory CRUD task API to SQLite, without copying from this guide. Specify: your lane and library, the table's columns, "create the table if missing," "seed three tasks only when empty," the five endpoints keeping identical behavior, the 400 and 404 rules, and parameterized queries.
2. Put the AI's version in `ai-version/` (or a branch). Your hand-built version stays untouched.
3. Run it and fire `bash tests/smoke.sh` at it. Does it create `tasks.db` on the first try? Does the seed run only once, or do the examples multiply on restart? Does the data survive a restart?
4. Diff it: `git diff --no-index app/sqlite_repository.py ai-version/<its file>`.
5. Add an "AI vs me" section to your README with your full prompt and at least three concrete differences:
   - What did it do better, and can you explain it?
   - What did it get wrong or quietly ignore (seeds that multiply, string-glued SQL, a changed status code)?
   - What did your prompt forget to specify, and what did the AI silently decide for you?
6. Rewrite your prompt once, regenerate, and note in one sentence what changed.

```bash
git add . && git commit -m "Stage 6: AI vs me"
```

---

## Final checklist

- [ ] Same five endpoints and response shapes as A1
- [ ] Tasks stored in SQLite (`tasks.db`), not in memory
- [ ] Data survives a restart, shown two ways: through the API and in DB Browser
- [ ] `tasks.db` and the `tasks` table are created automatically
- [ ] Three tasks seeded only on the first run, with no duplicates after restarts
- [ ] Every query uses `?` placeholders, with no user input glued into SQL
- [ ] Status codes carried over: 200 / 201 / 204 success, 400 invalid body, 404 unknown id, each error with JSON
- [ ] `bash tests/smoke.sh` passes against both the in-memory and SQLite versions
- [ ] Public repo with README (why SQLite, run command, a SQL query you ran, DB Browser screenshot)
- [ ] `git log` shows one commit per stage, and `tasks.db` is not tracked

## Troubleshooting

| Problem | Fix |
|---|---|
| Seeds multiply on every restart | The count check is missing or runs after the insert. Count first, insert only if it's 0. |
| `database is locked` | A connection was left open. Use the `_connection()` helper so every connection is closed, and close DB Browser's pending edits (Write Changes). |
| Changes in DB Browser don't appear in the API | You didn't click **Write Changes** (Ctrl+S). |
| `done` shows `0` / `1` instead of `false` / `true` | Convert in the repository with `bool(row["done"])`, as in `_to_task`. |
| `tasks.db` is in your Git history | Add it to `.gitignore` and run `git rm --cached tasks.db`. |
| Tests passed before the swap and fail now | Compare status codes first. A changed status code usually means the repository returns `None` or a different shape than the service expects. |
