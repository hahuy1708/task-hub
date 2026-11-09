from datetime import datetime

from pydantic import ConfigDict, Field

from task_hub.core.constants import WORKSPACE_NAME_MAX_LENGTH, WORKSPACE_NAME_MIN_LENGTH
from task_hub.models.enums import WorkspaceRole
from task_hub.schemas.base import BaseSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(
        min_length=WORKSPACE_NAME_MIN_LENGTH, max_length=WORKSPACE_NAME_MAX_LENGTH
    )


class WorkspaceUpdate(WorkspaceCreate):
    pass


class WorkspaceRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime


class WorkspaceMemberAdd(BaseSchema):
    user_id: int = Field(ge=1)
    role: WorkspaceRole = WorkspaceRole.VIEWER


class WorkspaceMemberRead(BaseSchema):
    workspace_id: int
    user_id: int
    email: str
    full_name: str
    role: WorkspaceRole
    joined_at: datetime
