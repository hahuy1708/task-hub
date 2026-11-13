from datetime import datetime

from pydantic import ConfigDict, Field

from task_hub.core.constants import COMMENT_CONTENT_MAX_LENGTH
from task_hub.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    content: str = Field(min_length=1, max_length=COMMENT_CONTENT_MAX_LENGTH)


class CommentRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
