from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.pagination import Pagination
from task_hub.models.comment import Comment


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, comment: Comment) -> Comment:
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_by_task(
        self, task_id: int, pagination: Pagination
    ) -> tuple[list[Comment], int]:
        result = await self.session.scalars(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.id)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        total = await self.session.scalar(
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        return list(result.all()), int(total or 0)

    async def get_by_id(self, comment_id: int) -> Comment | None:
        return await self.session.get(Comment, comment_id)

    async def delete(self, comment: Comment) -> None:
        await self.session.delete(comment)
