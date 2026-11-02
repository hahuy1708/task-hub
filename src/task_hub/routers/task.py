from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from task_hub.dependencies import TaskServiceDep
from task_hub.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])
TaskId = Annotated[int, Path(ge=1)]


@router.get("")
def list_tasks(
    service: TaskServiceDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[TaskRead]:
    return [TaskRead.model_validate(task) for task in service.list_tasks(skip, limit)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(service.create_task(data))


@router.get("/{task_id}")
def get_task(task_id: TaskId, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(service.get_task(task_id))


@router.patch("/{task_id}")
def update_task(task_id: TaskId, data: TaskUpdate, service: TaskServiceDep) -> TaskRead:
    return TaskRead.model_validate(service.update_task(task_id, data))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: TaskId, service: TaskServiceDep) -> None:
    service.delete_task(task_id)
