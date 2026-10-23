from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from supabase import AuthApiError

from app.supabase_client import new_client
from app.errors import ApiError
from app.schemas import Credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    new_client()  # fails loudly if the URL or key is malformed
    print("Server running and connected to Supabase")
    yield


app = FastAPI(title="Auth API", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


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