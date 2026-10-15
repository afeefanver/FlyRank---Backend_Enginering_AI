CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);

-- Optional: Index for faster title-based queries
CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks (title);