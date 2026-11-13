from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.models.label import Label
from task_hub.models.task import Task
from task_hub.schemas.label import LabelUpdate


class LabelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, label: Label) -> Label:
        self.session.add(label)
        await self.session.flush()
        return label

    async def get_by_id(self, label_id: int) -> Label | None:
        return await self.session.get(Label, label_id)

    async def list_by_project(self, project_id: int) -> list[Label]:
        result = await self.session.scalars(
            select(Label).where(Label.project_id == project_id).order_by(Label.id)
        )
        return list(result.all())

    async def save(self, label: Label, data: LabelUpdate) -> Label:
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(label, name, value)
        await self.session.flush()
        return label

    async def delete(self, label: Label) -> None:
        await self.session.delete(label)

    async def is_attached(self, task: Task, label_id: int) -> bool:
        return (
            await self.session.scalar(
                select(Task.id)
                .join(Task.labels)
                .where(Task.id == task.id, Label.id == label_id)
            )
            is not None
        )
