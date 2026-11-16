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
from task_hub.schemas.page import Page
from task_hub.schemas.task import TaskCreate, TaskRead, TaskUpdate
from task_hub.services.notifications import TaskNotifier
from task_hub.services.task_cache import TaskListCache, task_list_field
from task_hub.services.workspace import WorkspaceService


class TaskService:
    def __init__(
        self,
        repository: TaskRepository,
        projects: ProjectRepository,
        workspaces: WorkspaceService,
        session: AsyncSession,
        cache: TaskListCache,
        notifier: TaskNotifier,
    ) -> None:
        self.repository = repository
        self.projects = projects
        self.workspaces = workspaces
        self.session = session
        self.cache = cache
        self.notifier = notifier

    async def list_tasks(
        self,
        project_id: int,
        user: User,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        pagination: Pagination,
    ) -> Page[TaskRead]:
        project = await self._get_project(project_id)
        # Kiểm tra quyền trước khi đọc cache, cache không được bỏ qua bước này.
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.VIEWER
        )
        field = task_list_field(
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            skip=pagination.skip,
            limit=pagination.limit,
        )
        cached = await self.cache.get(project_id, field)
        if cached is not None:
            return cached
        tasks, total = await self.repository.list_by_project(
            project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            pagination=pagination,
        )
        page = Page[TaskRead](
            items=[TaskRead.model_validate(task) for task in tasks],
            total=total,
        )
        await self.cache.set(project_id, field, page)
        return page

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
        await self.session.refresh(task, attribute_names=["labels"])
        await self.cache.invalidate(project.id)
        await self._notify_new_assignee(task, user, previous_assignee_id=None)
        return task

    async def get_task(self, task_id: int, user: User) -> Task:
        task, _ = await self._get_task_for_user(task_id, user, WorkspaceRole.VIEWER)
        return task

    async def update_task(self, task_id: int, user: User, data: TaskUpdate) -> Task:
        task, project = await self._get_task_for_user(
            task_id, user, WorkspaceRole.EDITOR
        )
        self._ensure_project_active(project)
        previous_assignee_id = task.assignee_id
        if "assignee_id" in data.model_fields_set:
            await self._validate_assignee(project, data.assignee_id)
        task = await self.repository.save(task, data)
        await self.session.commit()
        await self.session.refresh(task, attribute_names=["labels"])
        await self.cache.invalidate(project.id)
        await self._notify_new_assignee(task, user, previous_assignee_id)
        return task

    async def delete_task(self, task_id: int, user: User) -> None:
        task, project = await self._get_task_for_user(
            task_id, user, WorkspaceRole.EDITOR
        )
        # Keep deletion available so archived projects can still be cleaned up.
        await self.repository.delete(task)
        await self.session.commit()
        await self.cache.invalidate(project.id)

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

    async def _notify_new_assignee(
        self, task: Task, actor: User, previous_assignee_id: int | None
    ) -> None:
        # Chỉ gửi khi có người mới được gán và không phải chính người thao tác.
        if task.assignee_id is None or task.assignee_id in (
            previous_assignee_id,
            actor.id,
        ):
            return
        assignee = await self.session.get(User, task.assignee_id)
        if assignee is None:
            return
        self.notifier.task_assigned(
            to_email=assignee.email, task_id=task.id, title=task.title
        )

    @staticmethod
    def _ensure_project_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)
