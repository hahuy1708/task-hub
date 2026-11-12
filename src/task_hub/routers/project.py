from typing import Annotated

from fastapi import APIRouter, Query, status

from task_hub.dependencies import CurrentUserDep, PaginationDep, ProjectServiceDep
from task_hub.models.enums import ProjectStatus
from task_hub.routers.types import ProjectId, WorkspaceId
from task_hub.schemas.page import Page
from task_hub.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(tags=["projects"])


@router.post(
    "/workspaces/{workspace_id}/projects",
    status_code=status.HTTP_201_CREATED,
    summary="Create a project in a workspace",
)
async def create_project(
    workspace_id: WorkspaceId,
    data: ProjectCreate,
    user: CurrentUserDep,
    service: ProjectServiceDep,
) -> ProjectRead:
    return ProjectRead.model_validate(
        await service.create_project(workspace_id, user, data)
    )


@router.get(
    "/workspaces/{workspace_id}/projects",
    summary="List projects in a workspace",
)
async def list_projects(
    workspace_id: WorkspaceId,
    user: CurrentUserDep,
    service: ProjectServiceDep,
    pagination: PaginationDep,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
) -> Page[ProjectRead]:
    projects, total = await service.list_projects(
        workspace_id,
        user,
        status=project_status,
        pagination=pagination,
    )
    return Page[ProjectRead](
        items=[ProjectRead.model_validate(project) for project in projects],
        total=total,
    )


@router.get("/projects/{project_id}", summary="Get a project")
async def get_project(
    project_id: ProjectId, user: CurrentUserDep, service: ProjectServiceDep
) -> ProjectRead:
    return ProjectRead.model_validate(await service.get_project(project_id, user))


@router.patch("/projects/{project_id}", summary="Update or archive a project")
async def update_project(
    project_id: ProjectId,
    data: ProjectUpdate,
    user: CurrentUserDep,
    service: ProjectServiceDep,
) -> ProjectRead:
    return ProjectRead.model_validate(
        await service.update_project(project_id, user, data)
    )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
async def delete_project(
    project_id: ProjectId, user: CurrentUserDep, service: ProjectServiceDep
) -> None:
    await service.delete_project(project_id, user)
