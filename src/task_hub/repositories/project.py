from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.pagination import Pagination
from task_hub.models.enums import ProjectStatus
from task_hub.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        return project

    async def get_by_id(self, project_id: int) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list_by_workspace(
        self,
        workspace_id: int,
        *,
        status: ProjectStatus | None,
        pagination: Pagination,
    ) -> tuple[list[Project], int]:
        conditions = [Project.workspace_id == workspace_id]
        if status is not None:
            conditions.append(Project.status == status)
        result = await self.session.scalars(
            select(Project)
            .where(*conditions)
            .order_by(Project.id)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        total = await self.session.scalar(
            select(func.count()).select_from(Project).where(*conditions)
        )
        return list(result.all()), int(total or 0)

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
