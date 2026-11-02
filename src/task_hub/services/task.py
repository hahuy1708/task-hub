from task_hub.models.task import Task, TaskPriority
from task_hub.schemas.task import TaskCreate, TaskUpdate


class NotFoundError(Exception):
    pass


class TaskService:
    def __init__(self) -> None:
        # in-memory data resets on restart
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self.create_task(
            TaskCreate(title="Thiết kế DB schema", priority=TaskPriority.HIGH)
        )
        self.create_task(TaskCreate(title="Viết API đăng nhập"))
        self.create_task(TaskCreate(title="Review code"))

    def list_tasks(self, skip: int, limit: int) -> list[Task]:
        return list(self._tasks.values())[skip : skip + limit]

    def get_task(self, task_id: int) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    def create_task(self, data: TaskCreate) -> Task:
        task = Task(id=self._next_id, **data.model_dump())
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def update_task(self, task_id: int, data: TaskUpdate) -> Task:
        task = self.get_task(task_id)
        # shortcut: null fields are ignored, so description cannot be cleared with null.
        for name, value in data.model_dump(
            exclude_unset=True, exclude_none=True
        ).items():
            setattr(task, name, value)
        return task

    def delete_task(self, task_id: int) -> None:
        self.get_task(task_id)
        del self._tasks[task_id]
