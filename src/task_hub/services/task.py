from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import NotFoundException
from task_hub.core.messages import TASK_NOT_FOUND
from task_hub.models.task import Task
from task_hub.repositories.task import TaskRepository
from task_hub.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository, session: AsyncSession) -> None:
        self.repository = repository
        self.session = session

    async def list_tasks(self, *, skip: int, limit: int) -> tuple[list[Task], int]:
        return await self.repository.list(skip=skip, limit=limit)

    async def get_task(self, task_id: int) -> Task:
        task = await self.repository.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND.format(task_id=task_id))
        return task

    async def create_task(self, data: TaskCreate) -> Task:
        task = await self.repository.add(data)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def update_task(self, task_id: int, data: TaskUpdate) -> Task:
        task = await self.get_task(task_id)
        task = await self.repository.save(task, data)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete_task(self, task_id: int) -> None:
        task = await self.get_task(task_id)
        await self.repository.delete(task)
        await self.session.commit()
