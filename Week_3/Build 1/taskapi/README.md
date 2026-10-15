# Task API

A task CRUD API built with FastAPI.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 3000
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /tasks | 200 | n/a |
| GET | /tasks/{id} | 200 | 404 |
| POST | /tasks | 201 | 400 |
| PUT | /tasks/{id} | 200 | 400, 404 |
| DELETE | /tasks/{id} | 204 | 404 |