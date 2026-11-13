from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnprocessableEntityException,
)
from task_hub.core.messages import (
    LABEL_ALREADY_ATTACHED,
    LABEL_NOT_FOUND,
    LABEL_PROJECT_MISMATCH,
    PROJECT_NOT_FOUND,
    TASK_NOT_FOUND,
)
from task_hub.models.enums import WorkspaceRole
from task_hub.models.label import Label
from task_hub.models.project import Project
from task_hub.models.task import Task
from task_hub.models.user import User
from task_hub.repositories.label import LabelRepository
from task_hub.repositories.project import ProjectRepository
from task_hub.repositories.task import TaskRepository
from task_hub.schemas.label import LabelCreate, LabelUpdate
from task_hub.services.workspace import WorkspaceService


class LabelService:
    def __init__(
        self,
        labels: LabelRepository,
        tasks: TaskRepository,
        projects: ProjectRepository,
        workspaces: WorkspaceService,
        session: AsyncSession,
    ) -> None:
        self.labels = labels
        self.tasks = tasks
        self.projects = projects
        self.workspaces = workspaces
        self.session = session

    async def list_labels(self, project_id: int, user: User) -> list[Label]:
        project = await self._get_project(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.VIEWER
        )
        return await self.labels.list_by_project(project_id)

    async def create_label(
        self, project_id: int, user: User, data: LabelCreate
    ) -> Label:
        project = await self._get_project(project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        try:
            label = await self.labels.add(
                Label(project_id=project_id, **data.model_dump())
            )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictException(
                "Label name already exists in this project"
            ) from None
        await self.session.refresh(label)
        return label

    async def update_label(self, label_id: int, user: User, data: LabelUpdate) -> Label:
        label = await self._get_label(label_id)
        project = await self._get_project(label.project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        try:
            await self.labels.save(label, data)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictException(
                "Label name already exists in this project"
            ) from None
        await self.session.refresh(label)
        return label

    async def delete_label(self, label_id: int, user: User) -> None:
        label = await self._get_label(label_id)
        project = await self._get_project(label.project_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        await self.labels.delete(label)
        await self.session.commit()

    async def attach_label(self, task_id: int, label_id: int, user: User) -> None:
        task, project = await self._get_task(task_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        label = await self._get_label(label_id)
        if label.project_id != project.id:
            raise UnprocessableEntityException(LABEL_PROJECT_MISMATCH)
        if await self.labels.is_attached(task, label_id):
            raise ConflictException(LABEL_ALREADY_ATTACHED)
        task.labels.append(label)
        await self.session.commit()

    async def detach_label(self, task_id: int, label_id: int, user: User) -> None:
        task, project = await self._get_task(task_id)
        await self.workspaces.check_access(
            project.workspace_id, user, WorkspaceRole.EDITOR
        )
        label = await self._get_label(label_id)
        if label.project_id != project.id:
            raise UnprocessableEntityException(LABEL_PROJECT_MISMATCH)
        if label in task.labels:
            task.labels.remove(label)
            await self.session.commit()

    async def _get_project(self, project_id: int) -> Project:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND.format(project_id=project_id))
        return project

    async def _get_label(self, label_id: int) -> Label:
        label = await self.labels.get_by_id(label_id)
        if label is None:
            raise NotFoundException(LABEL_NOT_FOUND.format(label_id=label_id))
        return label

    async def _get_task(self, task_id: int) -> tuple[Task, Project]:
        task_project = await self.tasks.get_with_project(task_id)
        if task_project is None:
            raise NotFoundException(TASK_NOT_FOUND.format(task_id=task_id))
        return task_project
