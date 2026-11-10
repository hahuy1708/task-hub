from enum import StrEnum


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SystemRole(StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class WorkspaceRole(StrEnum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

    @property
    def priority(self) -> int:
        return {
            WorkspaceRole.VIEWER: 1,
            WorkspaceRole.EDITOR: 2,
            WorkspaceRole.OWNER: 3,
        }[self]


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
