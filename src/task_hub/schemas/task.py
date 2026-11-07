from datetime import date, datetime

from pydantic import ConfigDict, Field, field_validator

from task_hub.core.constants import (
    TASK_DESCRIPTION_MAX_LENGTH,
    TASK_TITLE_MAX_LENGTH,
    TASK_TITLE_MIN_LENGTH,
)
from task_hub.core.messages import (
    TASK_DUE_DATE_IN_PAST,
    TASK_FIELD_CANNOT_BE_NULL,
)
from task_hub.models.enums import TaskPriority, TaskStatus
from task_hub.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    title: str = Field(
        min_length=TASK_TITLE_MIN_LENGTH, max_length=TASK_TITLE_MAX_LENGTH
    )
    description: str | None = Field(
        default=None, max_length=TASK_DESCRIPTION_MAX_LENGTH
    )
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_must_not_be_in_the_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError(TASK_DUE_DATE_IN_PAST)
        return value


class TaskUpdate(BaseSchema):
    title: str | None = Field(
        default=None,
        min_length=TASK_TITLE_MIN_LENGTH,
        max_length=TASK_TITLE_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None, max_length=TASK_DESCRIPTION_MAX_LENGTH
    )
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None

    @field_validator("title", "status", "priority", mode="before")
    @classmethod
    def reject_null_for_non_nullable_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError(TASK_FIELD_CANNOT_BE_NULL)
        return value

    @field_validator("due_date")
    @classmethod
    def due_date_must_not_be_in_the_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError(TASK_DUE_DATE_IN_PAST)
        return value


class TaskRead(BaseSchema):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    created_at: datetime
