from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from task_hub.core.constants import (
    PROJECT_LIST_DEFAULT_LIMIT,
    PROJECT_LIST_DEFAULT_SKIP,
    PROJECT_LIST_MAX_LIMIT,
)
from task_hub.dependencies import CurrentUserDep, ProjectServiceDep
from task_hub.models.enums import ProjectStatus
from task_hub.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(tags=["projects"])
ProjectId = Annotated[int, Path(ge=1)]
WorkspaceId = Annotated[int, Path(ge=1)]


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
    responses={
        200: {
            "headers": {
                "X-Total-Count": {
                    "description": (
                        "Total number of matching projects before pagination."
                    ),
                    "schema": {"type": "integer"},
                }
            }
        }
    },
)
async def list_projects(
    workspace_id: WorkspaceId,
    user: CurrentUserDep,
    service: ProjectServiceDep,
    response: Response,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    skip: Annotated[int, Query(ge=0)] = PROJECT_LIST_DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=1, le=PROJECT_LIST_MAX_LIMIT)] = (
        PROJECT_LIST_DEFAULT_LIMIT
    ),
) -> list[ProjectRead]:
    projects, total = await service.list_projects(
        workspace_id,
        user,
        status=project_status,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [ProjectRead.model_validate(project) for project in projects]


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
