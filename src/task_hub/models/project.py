from datetime import UTC, datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from task_hub.core.constants import PROJECT_NAME_MAX_LENGTH
from task_hub.models.base import Base
from task_hub.models.enums import ProjectStatus
from task_hub.models.types import UTCDateTime


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(PROJECT_NAME_MAX_LENGTH), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
