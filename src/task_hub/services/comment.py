from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import (
    ForbiddenException,
    NotFoundException,
)
from task_hub.core.messages import (
    COMMENT_DELETE_FORBIDDEN,
    COMMENT_NOT_FOUND,
    TASK_NOT_FOUND,
)
from task_hub.models.comment import Comment
from task_hub.models.enums import SystemRole, WorkspaceRole
from task_hub.models.project import Project
from task_hub.models.task import Task
from task_hub.models.user import User
from task_hub.repositories.comment import CommentRepository
from task_hub.repositories.task import TaskRepository
from task_hub.schemas.comment import CommentCreate
from task_hub.services.workspace import WorkspaceService


class CommentService:
    def __init__(
        self,
        comments: CommentRepository,
        tasks: TaskRepository,
        workspaces: WorkspaceService,
        session: AsyncSession,
    ) -> None:
        self.comments = comments
        self.tasks = tasks
        self.workspaces = workspaces
        self.session = session

    async def list_comments(self, task_id: int, user: User) -> list[Comment]:
        _, project = await self._get_task(task_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.VIEWER
        )
        return await self.comments.list_by_task(task_id)

    async def create_comment(
        self, task_id: int, user: User, data: CommentCreate
    ) -> Comment:
        _, project = await self._get_task(task_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        comment = await self.comments.add(
            Comment(task_id=task_id, author_id=user.id, content=data.content)
        )
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def delete_comment(self, comment_id: int, user: User) -> None:
        comment = await self.comments.get_by_id(comment_id)
        if comment is None:
            raise NotFoundException(COMMENT_NOT_FOUND.format(comment_id=comment_id))
        _, project = await self._get_task(comment.task_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.VIEWER
        )
        if comment.author_id != user.id and user.role != SystemRole.ADMIN:
            try:
                await self.workspaces.check_access(
                    project.workspace_id, user, WorkspaceRole.OWNER
                )
            except ForbiddenException:
                raise ForbiddenException(COMMENT_DELETE_FORBIDDEN) from None
        await self.comments.delete(comment)
        await self.session.commit()

    async def _get_task(self, task_id: int) -> tuple[Task, Project]:
        task_project = await self.tasks.get_with_project(task_id)
        if task_project is None:
            raise NotFoundException(TASK_NOT_FOUND.format(task_id=task_id))
        return task_project
