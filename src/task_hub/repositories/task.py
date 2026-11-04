from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.models.task import Task
from task_hub.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, *, skip: int, limit: int) -> list[Task]:
        result = await self.session.scalars(
            select(Task).order_by(Task.id).offset(skip).limit(limit)
        )
        return list(result.all())

    async def get(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def add(self, data: TaskCreate) -> Task:
        task = Task(**data.model_dump())
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def save(self, task: Task, data: TaskUpdate) -> Task:
        for name, value in data.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            setattr(task, name, value)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.commit()
