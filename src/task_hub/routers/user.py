from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from task_hub.core.constants import (
    AUTH_USER_LIST_DEFAULT_LIMIT,
    AUTH_USER_LIST_DEFAULT_SKIP,
    AUTH_USER_LIST_MAX_LIMIT,
)
from task_hub.dependencies import AdminDep, CurrentUserDep, SessionDep
from task_hub.repositories.user import UserRepository
from task_hub.schemas.user import ChangePasswordRequest, UserRead, UserUpdate
from task_hub.services.user import UserService

router = APIRouter(tags=["users"])


@router.get("", summary="List users (admin only)")
async def list_users(
    _: AdminDep,
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = AUTH_USER_LIST_DEFAULT_SKIP,
    limit: Annotated[int, Query(ge=1, le=AUTH_USER_LIST_MAX_LIMIT)] = (
        AUTH_USER_LIST_DEFAULT_LIMIT
    ),
) -> list[UserRead]:
    users = await UserRepository(session).list_all(skip=skip, limit=limit)
    return [UserRead.model_validate(user) for user in users]


@router.get("/me", summary="Get current user")
async def get_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", summary="Update current user")
async def update_me(
    data: UserUpdate, user: CurrentUserDep, session: SessionDep
) -> UserRead:
    updated_user = await UserService(session).update_me(user, data)
    return UserRead.model_validate(updated_user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
)
async def change_password(
    data: ChangePasswordRequest, user: CurrentUserDep, session: SessionDep
) -> Response:
    await UserService(session).change_password(user, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
