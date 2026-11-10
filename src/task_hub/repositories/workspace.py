from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.models.user import User
from task_hub.models.workspace import Workspace, WorkspaceMember


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def get_by_id(self, workspace_id: int) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def list_for_user(
        self, user_id: int, *, skip: int, limit: int
    ) -> tuple[list[Workspace], int]:
        statement = (
            select(Workspace)
            .join(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.scalars(statement)
        total = await self.session.scalar(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
        )
        return list(result.all()), int(total or 0)

    async def list_all(self, *, skip: int, limit: int) -> tuple[list[Workspace], int]:
        result = await self.session.scalars(
            select(Workspace).order_by(Workspace.id).offset(skip).limit(limit)
        )
        total = await self.session.scalar(select(func.count()).select_from(Workspace))
        return list(result.all()), int(total or 0)

    async def delete(self, workspace: Workspace) -> None:
        await self.session.delete(workspace)


class WorkspaceMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, member: WorkspaceMember) -> WorkspaceMember:
        self.session.add(member)
        await self.session.flush()
        return member

    async def get(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        return await self.session.get(WorkspaceMember, (workspace_id, user_id))

    async def list_by_workspace(
        self, workspace_id: int
    ) -> list[tuple[WorkspaceMember, User]]:
        result = await self.session.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at, User.id)
        )
        return list(result.all())

    async def delete(self, member: WorkspaceMember) -> None:
        await self.session.delete(member)
