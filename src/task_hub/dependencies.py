from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from task_hub.services.task import TaskService


@lru_cache
def get_task_service() -> TaskService:
    return TaskService()


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
