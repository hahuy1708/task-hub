from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.models.enums import TaskPriority, TaskStatus
from task_hub.models.task import Task
from task_hub.schemas.task import TaskUpdate


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(
        self,
        project_id: int,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Task], int]:
        conditions = [Task.project_id == project_id]
        if status is not None:
            conditions.append(Task.status == status)
        if priority is not None:
            conditions.append(Task.priority == priority)
        if assignee_id is not None:
            conditions.append(Task.assignee_id == assignee_id)
        result = await self.session.scalars(
            select(Task).where(*conditions).order_by(Task.id).offset(skip).limit(limit)
        )
        tasks = list(result.all())
        total = await self.session.scalar(
            select(func.count()).select_from(Task).where(*conditions)
        )
        return tasks, int(total or 0)

    async def get(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def add(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        return task

    async def save(self, task: Task, data: TaskUpdate) -> Task:
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(task, name, value)
        await self.session.flush()
        return task

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
