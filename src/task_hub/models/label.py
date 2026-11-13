from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from task_hub.core.constants import LABEL_COLOR_MAX_LENGTH, LABEL_NAME_MAX_LENGTH
from task_hub.models.base import Base

if TYPE_CHECKING:
    from task_hub.models.task import Task


task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)


class Label(Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(LABEL_NAME_MAX_LENGTH), nullable=False)
    color: Mapped[str] = mapped_column(String(LABEL_COLOR_MAX_LENGTH), nullable=False)
    tasks: Mapped[list[Task]] = relationship(
        secondary=task_labels, back_populates="labels"
    )
