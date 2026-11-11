from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from task_hub.core.constants import (
    TASK_ID_MIN,
    TASK_LIST_DEFAULT_LIMIT,
    TASK_LIST_DEFAULT_SKIP,
    TASK_LIST_MAX_LIMIT,
    TASK_LIST_MIN_LIMIT,
    TASK_SKIP_MIN,
)
from task_hub.dependencies import TaskServiceDep
from task_hub.schemas.task import TaskCreate, TaskListRead, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])
TaskId = Annotated[int, Path(ge=TASK_ID_MIN)]


@router.get("", summary="List tasks")
async def list_tasks(
    service: TaskServiceDep,
    skip: Annotated[int, Query(ge=TASK_SKIP_MIN)] = TASK_LIST_DEFAULT_SKIP,
    limit: Annotated[
        int, Query(ge=TASK_LIST_MIN_LIMIT, le=TASK_LIST_MAX_LIMIT)
    ] = TASK_LIST_DEFAULT_LIMIT,
) -> TaskListRead:
    tasks, total = await service.list_tasks(skip=skip, limit=limit)
    return TaskListRead(
        items=[TaskRead.model_validate(task) for task in tasks],
        total=total,
    )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a task")
async def create_task(data: TaskCreate, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(await service.create_task(data))


@router.get(
    "/{task_id}",
    summary="Get a task",
    responses={404: {"description": "Task not found"}},
)
async def get_task(task_id: TaskId, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(await service.get_task(task_id))


@router.patch(
    "/{task_id}",
    summary="Update a task",
    responses={404: {"description": "Task not found"}},
)
async def update_task(
    task_id: TaskId, data: TaskUpdate, service: TaskServiceDep
) -> TaskRead:
    return TaskRead.model_validate(await service.update_task(task_id, data))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    responses={404: {"description": "Task not found"}},
)
async def delete_task(task_id: TaskId, service: TaskServiceDep) -> None:
    await service.delete_task(task_id)
