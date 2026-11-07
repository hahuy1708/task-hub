from datetime import datetime

from pydantic import ConfigDict, Field

from task_hub.core.constants import (
    AUTH_FULL_NAME_MAX_LENGTH,
    AUTH_PASSWORD_MAX_LENGTH,
    AUTH_PASSWORD_MIN_LENGTH,
)
from task_hub.models.enums import SystemRole
from task_hub.schemas.base import BaseSchema


class UserRead(BaseSchema):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)

    id: int
    email: str
    full_name: str
    role: SystemRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseSchema):
    full_name: str | None = Field(
        default=None, min_length=1, max_length=AUTH_FULL_NAME_MAX_LENGTH
    )


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(
        min_length=AUTH_PASSWORD_MIN_LENGTH, max_length=AUTH_PASSWORD_MAX_LENGTH
    )
