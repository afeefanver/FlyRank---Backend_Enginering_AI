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