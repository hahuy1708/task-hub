from pydantic import ConfigDict, Field

from task_hub.core.constants import LABEL_COLOR_MAX_LENGTH, LABEL_NAME_MAX_LENGTH
from task_hub.schemas.base import BaseSchema


class LabelCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=LABEL_NAME_MAX_LENGTH)
    color: str = Field(min_length=1, max_length=LABEL_COLOR_MAX_LENGTH)


class LabelUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=1, max_length=LABEL_NAME_MAX_LENGTH
    )
    color: str | None = Field(
        default=None, min_length=1, max_length=LABEL_COLOR_MAX_LENGTH
    )


class LabelRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str
