from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from task_hub.dependencies import TaskServiceDep
from task_hub.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])
TaskId = Annotated[int, Path(ge=1)]


@router.get("")
async def list_tasks(
    service: TaskServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TaskRead]:
    tasks = await service.list_tasks(skip=skip, limit=limit)
    return [TaskRead.model_validate(task) for task in tasks]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(await service.create_task(data))


@router.get("/{task_id}")
async def get_task(task_id: TaskId, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(await service.get_task(task_id))


@router.patch("/{task_id}")
async def update_task(
    task_id: TaskId, data: TaskUpdate, service: TaskServiceDep
) -> TaskRead:
    return TaskRead.model_validate(await service.update_task(task_id, data))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: TaskId, service: TaskServiceDep) -> None:
    await service.delete_task(task_id)
