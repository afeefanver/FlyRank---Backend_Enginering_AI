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

FastAPI serves Swagger at `http://localhost:3000/docs`. Because `get_current_user` depends on
`HTTPBearer`, the padlock already appears on every route that uses it.

## Security notes

- `.env` is git-ignored, and only `.env.example` is committed.
- Only the anon key is used.
- Any verification error is treated as "not allowed" (the guard fails closed).