from fastapi import APIRouter, Response, status

from task_hub.dependencies import AuthServiceDep
from task_hub.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from task_hub.schemas.user import UserRead

router = APIRouter(tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register")
async def register(data: RegisterRequest, service: AuthServiceDep) -> UserRead:
    user = await service.register(data)
    return UserRead.model_validate(user)


@router.post("/login", summary="Login")
async def login(data: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.login(data)


@router.post("/refresh", summary="Refresh tokens")
async def refresh(data: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout")
async def logout(data: RefreshRequest, service: AuthServiceDep) -> Response:
    await service.logout(data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
