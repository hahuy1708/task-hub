from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.constants import WORKSPACE_ROLE_PRIORITY
from task_hub.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from task_hub.core.messages import (
    USER_NOT_FOUND,
    WORKSPACE_ACCESS_DENIED,
    WORKSPACE_MEMBER_EXISTS,
    WORKSPACE_MEMBER_NOT_FOUND,
    WORKSPACE_NOT_FOUND,
    WORKSPACE_OWNER_CANNOT_LEAVE,
)
from task_hub.models.enums import SystemRole, WorkspaceRole
from task_hub.models.user import User
from task_hub.models.workspace import Workspace, WorkspaceMember
from task_hub.repositories.user import UserRepository
from task_hub.repositories.workspace import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from task_hub.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspaces = WorkspaceRepository(session)
        self.members = WorkspaceMemberRepository(session)
        self.users = UserRepository(session)

    async def create_workspace(self, user: User, data: WorkspaceCreate) -> Workspace:
        workspace = await self.workspaces.add(
            Workspace(name=data.name, owner_id=user.id)
        )
        await self.members.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )
        )
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def list_workspaces(
        self, user: User, *, skip: int, limit: int
    ) -> tuple[list[Workspace], int]:
        if user.role == SystemRole.ADMIN:
            return await self.workspaces.list_all(skip=skip, limit=limit)
        return await self.workspaces.list_for_user(user.id, skip=skip, limit=limit)

    async def get_workspace(self, workspace_id: int, user: User) -> Workspace:
        return await self.check_access(workspace_id, user, WorkspaceRole.VIEWER)

    async def update_workspace(
        self, workspace_id: int, user: User, data: WorkspaceUpdate
    ) -> Workspace:
        workspace = await self.check_access(workspace_id, user, WorkspaceRole.OWNER)
        workspace.name = data.name
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace_id: int, user: User) -> None:
        workspace = await self.check_access(workspace_id, user, WorkspaceRole.OWNER)
        await self.workspaces.delete(workspace)
        await self.session.commit()

    async def list_members(
        self, workspace_id: int, user: User
    ) -> list[tuple[WorkspaceMember, User]]:
        await self.check_access(workspace_id, user, WorkspaceRole.VIEWER)
        return await self.members.list_by_workspace(workspace_id)

    async def add_member(
        self, workspace_id: int, user: User, data: WorkspaceMemberAdd
    ) -> tuple[WorkspaceMember, User]:
        await self.check_access(workspace_id, user, WorkspaceRole.OWNER)
        target = await self.users.get_by_id(data.user_id)
        if target is None or not target.is_active:
            raise NotFoundException(USER_NOT_FOUND.format(user_id=data.user_id))
        if await self.members.get(workspace_id, target.id):
            raise ConflictException(
                WORKSPACE_MEMBER_EXISTS.format(user_id=data.user_id)
            )
        member = await self.members.add(
            WorkspaceMember(
                workspace_id=workspace_id,
                user_id=target.id,
                role=data.role,
            )
        )
        await self.session.commit()
        await self.session.refresh(member)
        return member, target

    async def remove_member(
        self, workspace_id: int, user: User, target_user_id: int
    ) -> None:
        workspace = await self.get_workspace_record(workspace_id)
        if target_user_id != user.id:
            await self.check_access(workspace_id, user, WorkspaceRole.OWNER)
        elif user.role != SystemRole.ADMIN:
            await self.check_access(workspace_id, user, WorkspaceRole.VIEWER)
        if target_user_id == workspace.owner_id:
            raise ConflictException(WORKSPACE_OWNER_CANNOT_LEAVE)
        member = await self.members.get(workspace_id, target_user_id)
        if member is None:
            raise NotFoundException(
                WORKSPACE_MEMBER_NOT_FOUND.format(user_id=target_user_id)
            )
        await self.members.delete(member)
        await self.session.commit()

    async def check_access(
        self, workspace_id: int, user: User, min_role: WorkspaceRole
    ) -> Workspace:
        workspace = await self.get_workspace_record(workspace_id)
        if user.role == SystemRole.ADMIN:
            return workspace
        member = await self.members.get(workspace_id, user.id)
        if (
            member is None
            or WORKSPACE_ROLE_PRIORITY[member.role.value]
            < (WORKSPACE_ROLE_PRIORITY[min_role.value])
        ):
            raise ForbiddenException(WORKSPACE_ACCESS_DENIED)
        return workspace

    async def get_workspace_record(self, workspace_id: int) -> Workspace:
        workspace = await self.workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundException(
                WORKSPACE_NOT_FOUND.format(workspace_id=workspace_id)
            )
        return workspace
