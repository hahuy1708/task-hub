from fastapi import APIRouter, Response, status

from task_hub.dependencies import SessionDep
from task_hub.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from task_hub.schemas.user import UserRead
from task_hub.services.auth import AuthService

router = APIRouter(tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Register")
async def register(data: RegisterRequest, session: SessionDep) -> UserRead:
    user = await AuthService(session).register(data)
    return UserRead.model_validate(user)


@router.post("/login", summary="Login")
async def login(data: LoginRequest, session: SessionDep) -> TokenResponse:
    return await AuthService(session).login(data)


@router.post("/refresh", summary="Refresh tokens")
async def refresh(data: RefreshRequest, session: SessionDep) -> TokenResponse:
    return await AuthService(session).refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Logout")
async def logout(data: RefreshRequest, session: SessionDep) -> Response:
    await AuthService(session).logout(data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
