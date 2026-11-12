from fastapi import APIRouter, Response, status

from task_hub.dependencies import (
    AdminDep,
    CurrentUserDep,
    PaginationDep,
    UserServiceDep,
)
from task_hub.schemas.user import (
    ChangePasswordRequest,
    UserListRead,
    UserRead,
    UserUpdate,
)

router = APIRouter(tags=["users"])


@router.get("", summary="List users (admin only)")
async def list_users(
    _: AdminDep,
    service: UserServiceDep,
    pagination: PaginationDep,
) -> UserListRead:
    users, total = await service.list_users(pagination=pagination)
    return UserListRead(
        items=[UserRead.model_validate(user) for user in users],
        total=total,
    )


@router.get("/me", summary="Get current user")
async def get_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", summary="Update current user")
async def update_me(
    data: UserUpdate, user: CurrentUserDep, service: UserServiceDep
) -> UserRead:
    updated_user = await service.update_me(user, data)
    return UserRead.model_validate(updated_user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
)
async def change_password(
    data: ChangePasswordRequest, user: CurrentUserDep, service: UserServiceDep
) -> Response:
    await service.change_password(user, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
