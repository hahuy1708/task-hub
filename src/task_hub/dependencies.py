from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import ForbiddenException, UnauthorizedException
from task_hub.core.messages import ADMIN_REQUIRED, INVALID_TOKEN, INVALID_TOKEN_TYPE
from task_hub.database import SessionFactory
from task_hub.models.enums import SystemRole
from task_hub.models.user import User
from task_hub.repositories.task import TaskRepository
from task_hub.repositories.user import UserRepository
from task_hub.security import decode_token
from task_hub.services.project import ProjectService
from task_hub.services.task import TaskService
from task_hub.services.workspace import WorkspaceService


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_task_service(session: SessionDep) -> TaskService:
    return TaskService(TaskRepository(session), session)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_workspace_service(session: SessionDep) -> WorkspaceService:
    return WorkspaceService(session)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_project_service(session: SessionDep) -> ProjectService:
    return ProjectService(session)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: SessionDep,
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedException(INVALID_TOKEN_TYPE)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise UnauthorizedException(INVALID_TOKEN) from None

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException(INVALID_TOKEN)
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_admin(current_user: CurrentUserDep) -> User:
    if current_user.role != SystemRole.ADMIN:
        raise ForbiddenException(ADMIN_REQUIRED)
    return current_user


AdminDep = Annotated[User, Depends(require_admin)]
