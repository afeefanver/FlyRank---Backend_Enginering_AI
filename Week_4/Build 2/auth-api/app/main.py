from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Header, Depends, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx

from supabase import AuthApiError

from app.config import SUPABASE_KEY, SUPABASE_URL
from app.supabase_client import new_client
from app.errors import ApiError
from app.schemas import Credentials
from app.security import CurrentUser, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    new_client()  # fails loudly if the URL or key is malformed
    print("Server running and connected to Supabase")
    yield


app = FastAPI(
    title="Auth API",
    description="Sign up, log in, log out, and token-protected routes (Supabase Auth).",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "name": "Auth API",
        "docs": "/docs",
        "endpoints": [
            "/auth/signup",
            "/auth/login",
            "/auth/logout",
            "/public/info",
            "/protected/profile",
            "/protected/dashboard",
        ],
    }


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