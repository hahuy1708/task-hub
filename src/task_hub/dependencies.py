from collections.abc import AsyncIterator
from typing import Annotated, cast

import jwt
from fastapi import BackgroundTasks, Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.constants import (
    TASK_LIST_DEFAULT_LIMIT,
    TASK_LIST_DEFAULT_SKIP,
    TASK_LIST_MAX_LIMIT,
    TASK_LIST_MIN_LIMIT,
    TASK_SKIP_MIN,
)
from task_hub.core.exceptions import ForbiddenException, UnauthorizedException
from task_hub.core.messages import ADMIN_REQUIRED, INVALID_TOKEN
from task_hub.core.pagination import Pagination
from task_hub.database import SessionFactory
from task_hub.models.enums import SystemRole, TokenType
from task_hub.models.user import User
from task_hub.repositories.comment import CommentRepository
from task_hub.repositories.label import LabelRepository
from task_hub.repositories.project import ProjectRepository
from task_hub.repositories.task import TaskRepository
from task_hub.repositories.user import UserRepository
from task_hub.security import decode_token
from task_hub.services.auth import AuthService
from task_hub.services.comment import CommentService
from task_hub.services.label import LabelService
from task_hub.services.notifications import TaskNotifier, send_task_assigned_email
from task_hub.services.project import ProjectService
from task_hub.services.task import TaskService
from task_hub.services.task_cache import TaskListCache
from task_hub.services.user import UserService
from task_hub.services.workspace import WorkspaceService


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_pagination(
    skip: Annotated[int, Query(ge=TASK_SKIP_MIN)] = TASK_LIST_DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=TASK_LIST_MIN_LIMIT, le=TASK_LIST_MAX_LIMIT)] = (
        TASK_LIST_DEFAULT_LIMIT
    ),
) -> Pagination:
    return Pagination(skip=skip, limit=limit)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


def get_redis(request: Request) -> Redis:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise RuntimeError("Redis client is not initialized")
    return cast(Redis, redis)


RedisDep = Annotated[Redis, Depends(get_redis)]


def get_task_list_cache(redis: RedisDep) -> TaskListCache:
    return TaskListCache(redis)


TaskListCacheDep = Annotated[TaskListCache, Depends(get_task_list_cache)]


class BackgroundTaskNotifier:
    """Đưa việc gửi thông báo vào BackgroundTasks, chạy sau khi response đã trả về."""

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._background_tasks = background_tasks

    def task_assigned(self, *, to_email: str, task_id: int, title: str) -> None:
        self._background_tasks.add_task(
            send_task_assigned_email, to_email, task_id, title
        )


def get_task_notifier(background_tasks: BackgroundTasks) -> TaskNotifier:
    return BackgroundTaskNotifier(background_tasks)


TaskNotifierDep = Annotated[TaskNotifier, Depends(get_task_notifier)]


def get_workspace_service(session: SessionDep) -> WorkspaceService:
    return WorkspaceService(session)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_task_service(
    session: SessionDep,
    workspaces: WorkspaceServiceDep,
    cache: TaskListCacheDep,
    notifier: TaskNotifierDep,
) -> TaskService:
    return TaskService(
        TaskRepository(session),
        ProjectRepository(session),
        workspaces,
        session,
        cache,
        notifier,
    )


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_project_service(
    session: SessionDep, workspaces: WorkspaceServiceDep
) -> ProjectService:
    return ProjectService(ProjectRepository(session), workspaces, session)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def get_label_service(
    session: SessionDep,
    workspaces: WorkspaceServiceDep,
    cache: TaskListCacheDep,
) -> LabelService:
    return LabelService(
        LabelRepository(session),
        TaskRepository(session),
        ProjectRepository(session),
        workspaces,
        session,
        cache,
    )


LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]


def get_comment_service(
    session: SessionDep, workspaces: WorkspaceServiceDep
) -> CommentService:
    return CommentService(
        CommentRepository(session), TaskRepository(session), workspaces, session
    )


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    session: SessionDep,
) -> User:
    try:
        payload = decode_token(credentials.credentials, TokenType.ACCESS)
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
