from pydantic import Field

from task_hub.schemas.base import BaseSchema


class Page[T](BaseSchema):
    items: list[T]
    total: int = Field(ge=0)
