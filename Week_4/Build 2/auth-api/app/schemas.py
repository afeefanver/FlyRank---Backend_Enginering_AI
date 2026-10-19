from pydantic import BaseModel


class Credentials(BaseModel):
    email: str | None = None
    password: str | None = None