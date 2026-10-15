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