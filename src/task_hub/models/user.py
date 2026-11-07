from datetime import UTC, datetime

from sqlalchemy import Boolean, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from task_hub.core.constants import AUTH_EMAIL_MAX_LENGTH, AUTH_FULL_NAME_MAX_LENGTH
from task_hub.models.base import Base
from task_hub.models.enums import SystemRole
from task_hub.models.types import UTCDateTime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(AUTH_EMAIL_MAX_LENGTH), nullable=False, unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(
        String(AUTH_FULL_NAME_MAX_LENGTH), nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[SystemRole] = mapped_column(
        Enum(SystemRole, name="system_role"),
        nullable=False,
        default=SystemRole.MEMBER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
