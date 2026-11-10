from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import NotFoundException
from task_hub.core.messages import PROJECT_NOT_FOUND
from task_hub.models.enums import ProjectStatus, WorkspaceRole
from task_hub.models.project import Project
from task_hub.models.user import User
from task_hub.repositories.project import ProjectRepository
from task_hub.schemas.project import ProjectCreate, ProjectUpdate
from task_hub.services.workspace import WorkspaceService


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        workspaces: WorkspaceService,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.projects = repository
        self.workspaces = workspaces

    async def create_project(
        self, workspace_id: int, user: User, data: ProjectCreate
    ) -> Project:
        await self.workspaces.check_access(workspace_id, user, WorkspaceRole.EDITOR)
        project = await self.projects.add(
            Project(workspace_id=workspace_id, **data.model_dump())
        )
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def list_projects(
        self,
        workspace_id: int,
        user: User,
        *,
        status: ProjectStatus | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Project], int]:
        await self.workspaces.check_access(workspace_id, user, WorkspaceRole.VIEWER)
        return await self.projects.list_by_workspace(
            workspace_id, status=status, skip=skip, limit=limit
        )

    async def get_project(self, project_id: int, user: User) -> Project:
        project = await self._get(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.VIEWER
        )
        return project

    async def update_project(
        self, project_id: int, user: User, data: ProjectUpdate
    ) -> Project:
        project = await self._get(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        for name, value in data.model_dump(exclude_unset=True).items():
            setattr(project, name, value)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def delete_project(self, project_id: int, user: User) -> None:
        project = await self._get(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.OWNER
        )
        await self.projects.delete(project)
        await self.session.commit()

    async def _get(self, project_id: int) -> Project:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND.format(project_id=project_id))
        return project
