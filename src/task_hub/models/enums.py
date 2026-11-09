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
