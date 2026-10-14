# Task API — My First CRUD API

A small REST API that manages a to-do list: **create, read, update and delete** tasks.
Built with **Python + FastAPI** for the FlyRank Internship (Backend Track · Week 2 · Assignment A1).

- Data lives **in memory only** (no database, no files). Restarting the server resets it.
- Interactive docs (Swagger UI) are available at `/docs`.

---

## Quick start

Requires **Python 3.10+**.

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
uvicorn main:app --reload
```

The server starts at **http://localhost:8000** and Swagger UI at **http://localhost:8000/docs**.

> `requirements.txt` contents: `fastapi` and `uvicorn` (generate with `pip freeze` or write by hand).

---

## Endpoints

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| GET | `/` | API info | 200 | – |
| GET | `/health` | Health check | 200 | – |
| GET | `/tasks` | List all tasks | 200 | – |
| GET | `/tasks/{id}` | Get one task | 200 | 404 |
| POST | `/tasks` | Create a task | 201 | 400 |
| PUT | `/tasks/{id}` | Update a task's `title` and/or `done` | 200 | 400, 404 |
| DELETE | `/tasks/{id}` | Delete a task | 204 (empty body) | 404 |

<!-- If you build extras, add rows here, e.g. GET /tasks?done=true, GET /stats, POST /reset -->

**Task shape**

```json
{ "id": 1, "title": "Buy milk", "done": false }
```

**Error shape** (all errors return JSON)

```json
{ "error": "Task 99 not found" }
```

**Validation rules:** `title` must be present and a non-empty string (whitespace-only is rejected) → otherwise `400`.

---

## Example: `curl -i`

<!-- Paste ONE real output from your own machine. Example command: -->

```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
```

```text
PASTE YOUR REAL OUTPUT HERE (status line, headers, body)
```

---

## Swagger UI

![Swagger UI screenshot](docs/swagger.png)

<!-- Save your screenshot as docs/swagger.png (create the docs/ folder) -->

The full CRUD cycle (create → list → update → delete) was tested in Swagger UI with **Try it out**.

---

## Project structure

```text
.
├── main.py            # the API (Stages 0–6)
├── requirements.txt
├── README.md
├── docs/
│   └── swagger.png
└── ai-version/        # AI-generated version (Stage 7, kept separate)
```

---

## Build log (one commit per stage)

| Stage | Commit message | What I did |
|---|---|---|
| 0 | `Stage 0: hello server` | Installed FastAPI, started a server on localhost:8000 |
| 1 | `Stage 1: root and health endpoints` | Added `GET /` and `GET /health` |
| 2 | `Stage 2: read endpoints with 404` | In-memory list, `GET /tasks`, `GET /tasks/{id}`, 404 JSON error |
| 3 | `Stage 3: create with validation` | `POST /tasks` with 201 and 400 validation |
| 4 | `Stage 4: full CRUD` | `PUT` and `DELETE` with 404/400/204 |
| 5 | `Stage 5: Swagger UI` | Endpoint descriptions, tested via `/docs` |
| 6 | `Stage 6: publish and docs` | Public repo and this README |
| 7 | `Stage 7: AI vs me` | AI rematch (see below) |

---

## Extras (optional)

<!-- Delete this section if you skip extras. Otherwise list what you built. -->

- [ ] Filtering: `GET /tasks?done=true`
- [ ] Search: `GET /tasks?search=milk`
- [ ] Stats: `GET /stats` → `{ "total": 7, "done": 3, "open": 4 }`
- [ ] Seed & reset: `POST /reset`
- [ ] Pagination: `GET /tasks?limit=2&offset=2`

### The mortality experiment

<!-- Do it: create a few tasks, restart the server, call GET /tasks. Then write exactly two sentences. -->

I created `<N>` tasks, restarted the server, and called `GET /tasks`. **WHAT HAPPENED** — **WHY** (e.g. the tasks lived in a Python list in RAM, which is wiped when the process exits).

### Why real APIs never return "everything" (pagination)

<!-- Only if you built pagination. Suggested points, put in your own words: -->

Returning every record at once gets slower and heavier as data grows: more memory on the server, more bandwidth, slower responses, and clients that may crash or freeze on huge payloads. Pagination (`limit` / `offset`) lets clients fetch only what they need.

---

## AI vs me (Stage 7 — the AI rematch)

I built the API above by hand (Stages 0–6). Then I asked an AI assistant to build the same API, kept its code in `ai-version/`, ran it, and compared.

### My prompt (v1)

<!-- Paste your FULL prompt, written from memory, not copied from the assignment. -->

```text
PASTE YOUR FULL PROMPT HERE
```

### Did the AI's version run?

<!-- Did it start on the first try? Run your Stage 4 curls against it. -->

| Check | Result |
|---|---|
| Starts on first try | ✅ / ❌ |
| `GET /tasks` → 200 | ✅ / ❌ |
| `GET /tasks/99` → 404 + JSON error | ✅ / ❌ |
| `POST /tasks` valid → 201 | ✅ / ❌ |
| `POST /tasks` `{}` → 400 | ✅ / ❌ |
| `PUT /tasks/{id}` → 200 | ✅ / ❌ |
| `DELETE /tasks/{id}` → 204, empty body | ✅ / ❌ |
| `/docs` works | ✅ / ❌ |

### Differences I found (diffed with `git diff --no-index main.py ai-version/main.py`)

**1. What did the AI do better — and can I explain it?**
- …

**2. What did it get wrong or quietly ignore from my prompt?**
- … (e.g. 422 instead of 400, `{"detail": ...}` instead of `{"error": ...}`, a database I never asked for)

**3. What did my prompt forget to specify — and what did the AI silently decide?**
- … (e.g. id generation, whitespace-only titles, PUT partial updates, port number)

### The rematch (prompt v2)

<!-- ONE sentence: what you changed in the prompt and what changed in the output. -->

I changed `…` in my prompt, and the regenerated code `…`.

### Takeaway

An AI's output is only as good as the specification — and I could only judge it because I had built the thing myself first.

---

## What I learned

<!-- 2–4 bullets in your own words, e.g. status codes, validation, path parameters, in-memory limits. -->

- …
- …

---

## Author

**Afeef Anver Sha** — Kerala, India
