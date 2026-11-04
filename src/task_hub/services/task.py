from task_hub.models.task import Task
from task_hub.repositories.task import TaskRepository
from task_hub.schemas.task import TaskCreate, TaskUpdate


class NotFoundError(Exception):
    pass


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def list_tasks(self, *, skip: int, limit: int) -> list[Task]:
        return await self.repository.list(skip=skip, limit=limit)

    async def get_task(self, task_id: int) -> Task:
        task = await self.repository.get(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def create_task(self, data: TaskCreate) -> Task:
        return await self.repository.add(data)

    async def update_task(self, task_id: int, data: TaskUpdate) -> Task:
        task = await self.get_task(task_id)
        return await self.repository.save(task, data)

    async def delete_task(self, task_id: int) -> None:
        task = await self.get_task(task_id)
        await self.repository.delete(task)
