from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from task_hub.core.constants import (
    WORKSPACE_LIST_DEFAULT_LIMIT,
    WORKSPACE_LIST_DEFAULT_SKIP,
    WORKSPACE_LIST_MAX_LIMIT,
)
from task_hub.dependencies import CurrentUserDep, WorkspaceServiceDep
from task_hub.schemas.page import Page
from task_hub.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
WorkspaceId = Annotated[int, Path(ge=1)]
UserId = Annotated[int, Path(ge=1)]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a workspace")
async def create_workspace(
    data: WorkspaceCreate, user: CurrentUserDep, service: WorkspaceServiceDep
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(await service.create_workspace(user, data))


@router.get("", summary="List my workspaces")
async def list_workspaces(
    user: CurrentUserDep,
    service: WorkspaceServiceDep,
    skip: Annotated[int, Query(ge=0)] = WORKSPACE_LIST_DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=1, le=WORKSPACE_LIST_MAX_LIMIT)] = (
        WORKSPACE_LIST_DEFAULT_LIMIT
    ),
) -> Page[WorkspaceRead]:
    workspaces, total = await service.list_workspaces(user, skip=skip, limit=limit)
    return Page[WorkspaceRead](
        items=[WorkspaceRead.model_validate(workspace) for workspace in workspaces],
        total=total,
    )


@router.get("/{workspace_id}", summary="Get a workspace")
async def get_workspace(
    workspace_id: WorkspaceId, user: CurrentUserDep, service: WorkspaceServiceDep
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(await service.get_workspace(workspace_id, user))


@router.patch("/{workspace_id}", summary="Rename a workspace")
async def update_workspace(
    workspace_id: WorkspaceId,
    data: WorkspaceUpdate,
    user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(
        await service.update_workspace(workspace_id, user, data)
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
async def delete_workspace(
    workspace_id: WorkspaceId, user: CurrentUserDep, service: WorkspaceServiceDep
) -> None:
    await service.delete_workspace(workspace_id, user)


@router.get("/{workspace_id}/members", summary="List workspace members")
async def list_members(
    workspace_id: WorkspaceId, user: CurrentUserDep, service: WorkspaceServiceDep
) -> list[WorkspaceMemberRead]:
    members = await service.list_members(workspace_id, user)
    return [
        WorkspaceMemberRead.from_member(member, member_user)
        for member, member_user in members
    ]


@router.post(
    "/{workspace_id}/members",
    status_code=status.HTTP_201_CREATED,
    summary="Add a workspace member",
)
async def add_member(
    workspace_id: WorkspaceId,
    data: WorkspaceMemberAdd,
    user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberRead:
    member, member_user = await service.add_member(workspace_id, user, data)
    return WorkspaceMemberRead.from_member(member, member_user)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove or leave a workspace",
)
async def remove_member(
    workspace_id: WorkspaceId,
    user_id: UserId,
    user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> None:
    await service.remove_member(workspace_id, user, user_id)
