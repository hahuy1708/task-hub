from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnprocessableEntityException,
)
from task_hub.core.messages import (
    PROJECT_ARCHIVED,
    PROJECT_NOT_FOUND,
    TASK_ASSIGNEE_NOT_MEMBER,
    TASK_NOT_FOUND,
)
from task_hub.core.pagination import Pagination
from task_hub.models.enums import ProjectStatus, TaskPriority, TaskStatus, WorkspaceRole
from task_hub.models.project import Project
from task_hub.models.task import Task
from task_hub.models.user import User
from task_hub.repositories.project import ProjectRepository
from task_hub.repositories.task import TaskRepository
from task_hub.schemas.task import TaskCreate, TaskUpdate
from task_hub.services.workspace import WorkspaceService


class TaskService:
    def __init__(
        self,
        repository: TaskRepository,
        projects: ProjectRepository,
        workspaces: WorkspaceService,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.projects = projects
        self.workspaces = workspaces
        self.session = session

    async def list_tasks(
        self,
        project_id: int,
        user: User,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        pagination: Pagination,
    ) -> tuple[list[Task], int]:
        project = await self._get_project(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.VIEWER
        )
        return await self.repository.list_by_project(
            project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            pagination=pagination,
        )

    async def create_task(self, project_id: int, user: User, data: TaskCreate) -> Task:
        project = await self._get_project(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        self._ensure_project_active(project)
        await self._validate_assignee(project, data.assignee_id)
        task = await self.repository.add(
            Task(
                project_id=project.id,
                created_by=user.id,
                **data.model_dump(),
            )
        )
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_task(self, task_id: int, user: User) -> Task:
        task, _ = await self._get_task_for_user(task_id, user, WorkspaceRole.VIEWER)
        return task

    async def update_task(self, task_id: int, user: User, data: TaskUpdate) -> Task:
        task, project = await self._get_task_for_user(
            task_id, user, WorkspaceRole.EDITOR
        )
        self._ensure_project_active(project)
        if "assignee_id" in data.model_fields_set:
            await self._validate_assignee(project, data.assignee_id)
        task = await self.repository.save(task, data)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def delete_task(self, task_id: int, user: User) -> None:
        task, _ = await self._get_task_for_user(task_id, user, WorkspaceRole.EDITOR)
        # Keep deletion available so archived projects can still be cleaned up.
        await self.repository.delete(task)
        await self.session.commit()

    async def _get_project(self, project_id: int) -> Project:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND.format(project_id=project_id))
        return project

    async def _get_task_for_user(
        self, task_id: int, user: User, min_role: WorkspaceRole
    ) -> tuple[Task, Project]:
        task_project = await self.repository.get_with_project(task_id)
        if task_project is None:
            raise NotFoundException(TASK_NOT_FOUND.format(task_id=task_id))
        task, project = task_project
        await self.workspaces.check_access(project.workspace_id, user, min_role)
        return task, project

    async def _validate_assignee(
        self, project: Project, assignee_id: int | None
    ) -> None:
        if assignee_id is not None and not await self.workspaces.is_member(
            project.workspace_id, assignee_id
        ):
            raise UnprocessableEntityException(TASK_ASSIGNEE_NOT_MEMBER)

    @staticmethod
    def _ensure_project_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)
