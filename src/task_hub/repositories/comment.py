from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.models.comment import Comment


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, comment: Comment) -> Comment:
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_by_task(self, task_id: int) -> list[Comment]:
        result = await self.session.scalars(
            select(Comment).where(Comment.task_id == task_id).order_by(Comment.id)
        )
        return list(result.all())

    async def get_by_id(self, comment_id: int) -> Comment | None:
        return await self.session.get(Comment, comment_id)

    async def delete(self, comment: Comment) -> None:
        await self.session.delete(comment)
