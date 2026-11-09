from datetime import datetime

from pydantic import ConfigDict, Field, field_validator

from task_hub.core.constants import (
    PROJECT_DESCRIPTION_MAX_LENGTH,
    PROJECT_NAME_MAX_LENGTH,
    PROJECT_NAME_MIN_LENGTH,
)
from task_hub.core.messages import TASK_FIELD_CANNOT_BE_NULL
from task_hub.models.enums import ProjectStatus
from task_hub.schemas.base import BaseSchema


class ProjectCreate(BaseSchema):
    name: str = Field(
        min_length=PROJECT_NAME_MIN_LENGTH, max_length=PROJECT_NAME_MAX_LENGTH
    )
    description: str | None = Field(
        default=None, max_length=PROJECT_DESCRIPTION_MAX_LENGTH
    )


class ProjectUpdate(BaseSchema):
    name: str | None = Field(
        default=None,
        min_length=PROJECT_NAME_MIN_LENGTH,
        max_length=PROJECT_NAME_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None, max_length=PROJECT_DESCRIPTION_MAX_LENGTH
    )
    status: ProjectStatus | None = None

    @field_validator("name", "status", mode="before")
    @classmethod
    def reject_null_for_non_nullable_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError(TASK_FIELD_CANNOT_BE_NULL)
        return value


class ProjectRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
