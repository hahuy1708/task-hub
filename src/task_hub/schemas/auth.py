from pydantic import EmailStr, Field

from task_hub.core.constants import (
    AUTH_EMAIL_MAX_LENGTH,
    AUTH_FULL_NAME_MAX_LENGTH,
    AUTH_PASSWORD_MAX_LENGTH,
    AUTH_PASSWORD_MIN_LENGTH,
)
from task_hub.schemas.base import BaseSchema


class RegisterRequest(BaseSchema):
    email: EmailStr = Field(max_length=AUTH_EMAIL_MAX_LENGTH)
    full_name: str = Field(min_length=1, max_length=AUTH_FULL_NAME_MAX_LENGTH)
    password: str = Field(
        min_length=AUTH_PASSWORD_MIN_LENGTH, max_length=AUTH_PASSWORD_MAX_LENGTH
    )


class LoginRequest(BaseSchema):
    email: EmailStr = Field(max_length=AUTH_EMAIL_MAX_LENGTH)
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseSchema):
    refresh_token: str
