# A4: Auth, Login and Protect (Supabase + FastAPI)

Build a secure API where users sign up, log in and log out through Supabase Auth, and where protected routes only open for a verified token. You document it in Swagger UI and publish it to GitHub.

**Assumptions in this guide (change them if they're wrong):**

- Python lane: FastAPI plus the `supabase` package.
- The server runs on port **3000** (set on the command line), so the curl examples match the assignment text. FastAPI's default is 8000 if you leave the flag off.
- You never store passwords or hash anything. Supabase does that.

If you use Node and Express instead, keep the stages, the status codes and the checkpoints, and tell me so I can write that version.

---

## The big idea

```
Client --(email + password)--> Supabase --(JWT access token)--> Client
Client --(Authorization: Bearer <token>)--> Your API --(is this token real?)--> Supabase
```

Your server never sees a password it has to keep. It forwards credentials to Supabase, and it verifies the token Supabase hands back.

---

## Target layout

```
auth-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # app, routes, error handlers
│   ├── config.py        # reads .env
│   ├── supabase_client.py
│   ├── security.py      # the reusable auth dependency (your "middleware")
│   └── schemas.py
├── .env                 # NOT committed
├── .env.example         # committed, placeholders only
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Stage 0: Set up Supabase and your server

1. Create a free project at supabase.com (for example, "Auth-Practice"). It takes a minute or two.
2. Open **Project Settings → API** and copy the **Project URL** and the **anon key**. Use the anon key only. The `service_role` key bypasses all security, so never put it in this project.
3. Turn off email confirmation for this practice project: **Authentication → Sign In / Providers → Email → Confirm email: off**. Otherwise a new user can't log in until they click a link.
4. Create the project folder and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install fastapi "uvicorn[standard]" supabase python-dotenv httpx
pip freeze > requirements.txt
```

5. `.gitignore` (create it **before** your first commit):

```
.env
.venv/
venv/
__pycache__/
*.pyc
```

6. `.env`:

```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your_anon_key
PORT=3000
```

7. `.env.example` (committed, placeholders only):

```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
PORT=3000
```

### `app/config.py`

```python
import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
PORT = int(os.getenv("PORT", "3000"))
```

### `app/supabase_client.py`

A **new client per request**, because the SDK stores the logged-in session inside the client object. If you used one shared client for everyone, one user's login could leak into another user's request.

```python
from supabase import Client, create_client

from app.config import SUPABASE_KEY, SUPABASE_URL


def new_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
```

### `app/main.py` (starter)

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.supabase_client import new_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    new_client()  # fails loudly if the URL or key is malformed
    print("Server running and connected to Supabase")
    yield


app = FastAPI(title="Auth API", lifespan=lifespan)
```

Add an empty `app/__init__.py`, then run:

```bash
uvicorn app.main:app --port 3000 --reload
```

**Checkpoint:** the server logs `Server running and connected to Supabase` with no errors, and `.env` is already in `.gitignore`.

```bash
git add . && git commit -m "Stage 0: setup server and supabase client"
```

---

## Stage 1: Sign up and log in

### `app/schemas.py`

```python
from pydantic import BaseModel


class Credentials(BaseModel):
    email: str | None = None
    password: str | None = None
```

### Shared error type and handlers

Add to `app/main.py`. FastAPI's default errors use `{"detail": ...}`, but the assignment wants `{"error": ...}`, so this makes every error look the same.

```python
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})
```

To avoid a circular import later, put `ApiError` in its own file. Create `app/errors.py` with the class above and import it in both `main.py` and `security.py`.

### Signup and login routes

```python
from supabase import AuthApiError   # if this import fails, see Troubleshooting

from app.errors import ApiError
from app.schemas import Credentials


@app.post("/auth/signup", status_code=201)
def signup(body: Credentials):
    if not body.email or not body.password:
        raise ApiError(400, "email and password are required")
    try:
        result = new_client().auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        raise ApiError(400, str(e))
    return result.user.model_dump(mode="json")


@app.post("/auth/login")
def login(body: Credentials):
    if not body.email or not body.password:
        raise ApiError(400, "email and password are required")
    try:
        result = new_client().auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError:
        raise ApiError(401, "Invalid login credentials")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }
```

Supabase rejects passwords shorter than 6 characters, so use something like `password123`.

**Checkpoint:**

```bash
# register -> 201
curl -i -X POST http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# missing password -> 400
curl -i -X POST http://localhost:3000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# login -> 200 with an access_token
curl -i -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# wrong password -> 401
curl -i -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrongpass"}'
```

```bash
git add . && git commit -m "Stage 1: signup and login routes working"
```

---

## Stage 2: The public gate and the (unverified) protected gate

First the open door, then a locked door that only checks a token was presented. Add to `app/main.py`:

```python
from fastapi import Header


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "Access token required")
    token = authorization[7:].strip()
    if not token:
        raise ApiError(401, "Access token required")
    return {"message": "a token was presented (not verified yet)"}
```

**Checkpoint:**

```bash
curl -i http://localhost:3000/public/info          # 200
curl -i http://localhost:3000/protected/profile    # 401, "Access token required"
```

```bash
git add . && git commit -m "Stage 2: public route and unverified protected route"
```

---

## Stage 3: The guard verifies the token

Replace the body of `/protected/profile` so it asks Supabase whether the token is real. Verifying with `get_user` makes a network call to Supabase, so the answer can be trusted.

```python
@app.get("/protected/profile")
def profile(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "Access token required")
    token = authorization[7:].strip()
    if not token:
        raise ApiError(401, "Access token required")

    try:
        result = new_client().auth.get_user(token)
        user = result.user if result else None
    except Exception:
        raise ApiError(401, "Invalid or expired token")
    if user is None:
        raise ApiError(401, "Invalid or expired token")

    return {"id": user.id, "email": user.email, "created_at": str(user.created_at)}
```

Note the `except Exception`. The guard fails closed: anything that goes wrong means "no entry". The common AI-written flaw is trusting a result without checking for an error.

**Checkpoint:**

```bash
TOKEN=$(curl -s -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# valid token -> 200 with your user details
curl -i http://localhost:3000/protected/profile -H "Authorization: Bearer $TOKEN"

# tampered token (last character changed) -> 401
curl -i http://localhost:3000/protected/profile -H "Authorization: Bearer ${TOKEN}x"
```

```bash
git add . && git commit -m "Stage 3: profile route token verification"
```

---

## Stage 4: Middleware (a FastAPI dependency) and logout

Move the guard into one reusable function so a route can't forget it.

### `app/security.py`

```python
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.errors import ApiError
from app.supabase_client import new_client

# auto_error=False lets us return our own {"error": ...} 401 instead of FastAPI's default.
# Using HTTPBearer is also what makes the Authorize padlock appear in Swagger (Stage 5).
bearer_scheme = HTTPBearer(auto_error=False, bearerFormat="JWT")


@dataclass
class CurrentUser:
    id: str
    email: str | None
    created_at: str
    token: str


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if creds is None or not creds.credentials:
        raise ApiError(401, "Access token required")

    token = creds.credentials
    try:
        result = new_client().auth.get_user(token)
        user = result.user if result else None
    except Exception:
        raise ApiError(401, "Invalid or expired token")
    if user is None:
        raise ApiError(401, "Invalid or expired token")

    return CurrentUser(
        id=user.id, email=user.email, created_at=str(user.created_at), token=token
    )
```

### Use it in `app/main.py`

Remove the hand-written checks from the profile route. Add a second protected route and logout:

```python
import httpx
from fastapi import Depends, Response

from app.config import SUPABASE_KEY, SUPABASE_URL
from app.security import CurrentUser, get_current_user


@app.get("/protected/profile")
def profile(user: CurrentUser = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@app.get("/protected/dashboard")
def dashboard(user: CurrentUser = Depends(get_current_user)):
    return {"message": f"Welcome back, {user.email}", "id": user.id}


@app.post("/auth/logout", status_code=204)
def logout(user: CurrentUser = Depends(get_current_user)):
    # The SDK's sign_out() signs out the *client's own* session, not the caller's token,
    # so we call Supabase's logout endpoint directly with the caller's token.
    response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/logout",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {user.token}"},
        timeout=10,
    )
    if response.status_code not in (200, 204):
        raise ApiError(502, "Logout failed")
    return Response(status_code=204)
```

**Checkpoint:** `/protected/dashboard` reuses the guard with zero new auth code.

```bash
curl -i http://localhost:3000/protected/dashboard                                  # 401
curl -i http://localhost:3000/protected/dashboard -H "Authorization: Bearer ${TOKEN}x"   # 401
curl -i http://localhost:3000/protected/dashboard -H "Authorization: Bearer $TOKEN"      # 200
curl -i -X POST http://localhost:3000/auth/logout -H "Authorization: Bearer $TOKEN"      # 204
```

```bash
git add . && git commit -m "Stage 4: auth middleware and logout endpoint"
```

---

## Stage 5: Swagger UI with the Authorize padlock

FastAPI serves Swagger at `http://localhost:3000/docs`. Because `get_current_user` depends on `HTTPBearer`, the padlock already appears on every route that uses it, so there is almost nothing to add.

1. Open `/docs`. You should see an **Authorize** button and a lock icon next to `/protected/profile`, `/protected/dashboard` and `/auth/logout`.
2. Log in (use "Try it out" on `/auth/login`), copy the `access_token`, click **Authorize**, paste **just the token** (Swagger adds `Bearer` for you), and click **Authorize**.
3. Use "Try it out" on `/protected/profile`. It returns `200`.
4. Take a screenshot of `/docs` showing the lock icons for your README.

Optional polish, in `main.py`:

```python
app = FastAPI(
    title="Auth API",
    description="Sign up, log in, log out, and token-protected routes (Supabase Auth).",
    lifespan=lifespan,
)
```

**Checkpoint:** `/docs` shows lock icons, you authorize with a token, and the profile endpoint works from the browser.

```bash
git add . && git commit -m "Stage 5: Swagger UI documentation with bearer auth"
```

---

## Stage 6: Publish to GitHub

1. Verify nothing secret was ever committed:

```bash
git ls-files | grep -E "^\.env$"        # must print nothing
git log --all --oneline -- .env          # must print nothing
```

If `.env` was ever committed, rotate your Supabase keys first (Project Settings → API), then remove the file from history before you push.

2. Create a public repo on GitHub, push, and clone it fresh into another folder to test:

```bash
git clone <your-repo-url> fresh && cd fresh
cp .env.example .env     # add your own values
pip install -r requirements.txt
uvicorn app.main:app --port 3000
```

3. Write the README (template below).

### README template

````markdown
# Auth API (Supabase + FastAPI)

A small API where users sign up, log in and log out through Supabase Auth, and where
protected routes only answer for a verified token. I don't store passwords or write any
crypto: Supabase is the identity provider, and my server verifies the tokens it issues.

## Setup

1. Create a free Supabase project. In Project Settings → API, copy the Project URL and the
   **anon** key. Never use the service_role key.
2. In Authentication → Sign In / Providers → Email, turn off "Confirm email" (practice only).
3. Copy `.env.example` to `.env` and fill in your values.

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 3000
```

Interactive docs: http://localhost:3000/docs

## API reference

| Method | Path | Auth needed | Success | Errors |
|---|---|---|---|---|
| POST | /auth/signup | No | 201 | 400 |
| POST | /auth/login | No | 200 | 400, 401 |
| POST | /auth/logout | Bearer token | 204 | 401 |
| GET | /protected/profile | Bearer token | 200 | 401 |
| GET | /protected/dashboard | Bearer token | 200 | 401 |
| GET | /public/info | No | 200 | n/a |

## How the guard works

`get_current_user` (in `app/security.py`) reads the `Authorization: Bearer <token>` header,
asks Supabase to verify the token, and either returns the user or answers 401. Every
protected route uses it with `Depends`, so no route can forget the check.

## Swagger UI

<screenshot of /docs showing the lock icons>

## Security notes

- `.env` is git-ignored, and only `.env.example` is committed.
- Only the anon key is used.
- Any verification error is treated as "not allowed" (the guard fails closed).
````

**Checkpoint:** a peer can clone the repo, add their own `.env`, and run the API in under 5 minutes.

```bash
git add . && git commit -m "Stage 6: publish to GitHub and write README"
git push
```

---

## Optional extras

### A 403 case (401 vs 403)

Create an admin-only route. `401` means "I don't know who you are." `403` means "I know who you are, and no."

```python
import os

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


@app.get("/protected/admin")
def admin(user: CurrentUser = Depends(get_current_user)):
    if not ADMIN_EMAIL or user.email != ADMIN_EMAIL:
        raise ApiError(403, "Forbidden")
    return {"message": "Welcome, admin"}
```

Add `ADMIN_EMAIL=you@example.com` to `.env` and `.env.example`.

### Refresh-token endpoint

```python
@app.post("/auth/refresh")
def refresh(body: dict):
    token = body.get("refresh_token")
    if not token:
        raise ApiError(400, "refresh_token is required")
    try:
        result = new_client().auth.refresh_session(token)
    except Exception:
        raise ApiError(401, "Invalid refresh token")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }
```

Access tokens are short-lived so that a stolen one stops working quickly. The refresh token gets you a new one without a new login.

### Read your own token

Paste an access token into jwt.io. A JWT's payload is only encoded, not encrypted, so anyone holding it can read it. Never put a secret inside one.

### A real logout test

Log out, then reuse the same token on `/protected/profile` and record exactly what happens. Because JWTs are stateless, "instant logout" is genuinely hard. Write two sentences on what you saw.

---

## Stage 7: The AI rematch (bonus)

1. Write your own prompt asking an AI to build the same API without copying from this guide. Specify: your framework, Supabase as the identity provider, the routes, the status codes (201 / 200 / 204 / 400 / 401), token verification through a reusable dependency, and the Swagger bearer setup.
2. Put the output in `ai-version/` (or a branch) and test your Stage 3 and Stage 4 checkpoints against it, with a valid token and a tampered one.
3. Diff it: `git diff --no-index app ai-version`.
4. Add an "AI vs me" section to your README with your full prompt and at least three differences:
   - How did it parse the `Bearer ` prefix? Would `Authorization: <token>` slip through or crash?
   - Does it safely reject an invalid token, or trust the result without checking for an error? Did it use the `service_role` key, or log the token?
   - What did your prompt forget to specify, and what did the AI silently decide?
5. Improve the prompt once, regenerate, and note in one sentence what changed.

```bash
git add . && git commit -m "Stage 7: AI vs me"
```

---

## Final checklist

- [ ] Server starts with one documented command and connects to Supabase
- [ ] `.env` is used and git-ignored, `.env.example` is committed, and no keys are in git history
- [ ] Signup and login talk to Supabase, and login returns an access token
- [ ] `/protected/profile` extracts and verifies the bearer token through Supabase
- [ ] Status codes: 201 signup, 200 login and reads, 204 logout, 400 missing input, 401 missing, malformed or invalid tokens, each with a JSON `error`
- [ ] The auth check is a reusable dependency used by more than one route
- [ ] Swagger at `/docs` shows lock icons, and Authorize works end to end
- [ ] The flow works twice: once through curl (including a tampered token returning 401) and once through Swagger
- [ ] Public repo, at least 6 clean commits, README with setup, run command, endpoint table and screenshot

## Troubleshooting

| Problem | Fix |
|---|---|
| `ImportError: cannot import name 'AuthApiError' from 'supabase'` | Your SDK version exports it elsewhere. Run `pip show supabase`, then try `from supabase_auth.errors import AuthApiError` (or `from gotrue.errors import AuthApiError` on older versions). |
| Signup returns an error about email rate limits | Supabase limits how many emails it sends per hour. Make sure "Confirm email" is off, and use a different test address such as `you+test2@gmail.com`. |
| Login says "Email not confirmed" | "Confirm email" is still on. Turn it off in the Supabase dashboard, or confirm the user manually in Authentication → Users. |
| `Password should be at least 6 characters` | Use a longer test password. |
| Swagger "Authorize" returns 401 | Paste only the token, without the word `Bearer`. Swagger adds it. Also check the token hasn't expired (one hour). |
| `/docs` shows no lock icon | The route doesn't use `Depends(get_current_user)`, or the dependency doesn't use `HTTPBearer`. |
| `KeyError: 'SUPABASE_URL'` | `.env` is missing or you ran the server from a different folder. |
| Users leak between requests | You are sharing one global Supabase client. Use `new_client()` per request. |
