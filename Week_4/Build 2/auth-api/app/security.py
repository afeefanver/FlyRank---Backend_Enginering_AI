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