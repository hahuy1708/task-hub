from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from task_hub.core.constants import TASK_ID_MIN
from task_hub.dependencies import CurrentUserDep, PaginationDep, TaskServiceDep
from task_hub.models.enums import TaskPriority, TaskStatus
from task_hub.routers.types import ProjectId
from task_hub.schemas.page import Page
from task_hub.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(tags=["tasks"])
TaskId = Annotated[int, Path(ge=TASK_ID_MIN)]


@router.get("/projects/{project_id}/tasks", summary="List tasks in a project")
async def list_tasks(
    project_id: ProjectId,
    user: CurrentUserDep,
    service: TaskServiceDep,
    pagination: PaginationDep,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    assignee_id: Annotated[int | None, Query(ge=TASK_ID_MIN)] = None,
) -> Page[TaskRead]:
    tasks, total = await service.list_tasks(
        project_id,
        user,
        status=task_status,
        priority=priority,
        assignee_id=assignee_id,
        pagination=pagination,
    )
    return Page[TaskRead](
        items=[TaskRead.model_validate(task) for task in tasks],
        total=total,
    )


@router.post(
    "/projects/{project_id}/tasks",
    status_code=status.HTTP_201_CREATED,
    summary="Create a task in a project",
)
async def create_task(
    project_id: ProjectId,
    data: TaskCreate,
    user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskRead:
    return TaskRead.model_validate(await service.create_task(project_id, user, data))


@router.get(
    "/tasks/{task_id}",
    summary="Get a task",
    responses={404: {"description": "Task not found"}},
)
async def get_task(
    task_id: TaskId, user: CurrentUserDep, service: TaskServiceDep
) -> TaskRead:
    return TaskRead.model_validate(await service.get_task(task_id, user))


@router.patch(
    "/tasks/{task_id}",
    summary="Update a task",
    responses={404: {"description": "Task not found"}},
)
async def update_task(
    task_id: TaskId,
    data: TaskUpdate,
    user: CurrentUserDep,
    service: TaskServiceDep,
) -> TaskRead:
    return TaskRead.model_validate(await service.update_task(task_id, user, data))


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    responses={404: {"description": "Task not found"}},
)
async def delete_task(
    task_id: TaskId, user: CurrentUserDep, service: TaskServiceDep
) -> None:
    await service.delete_task(task_id, user)
