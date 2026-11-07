from typing import Any

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import (
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
)
from task_hub.core.messages import (
    ACCOUNT_DEACTIVATED,
    EMAIL_ALREADY_REGISTERED,
    INVALID_CREDENTIALS,
    INVALID_TOKEN,
    INVALID_TOKEN_TYPE,
    TOKEN_REVOKED_OR_EXPIRED,
)
from task_hub.models.user import User
from task_hub.repositories.refresh_token import RefreshTokenRepository
from task_hub.repositories.user import UserRepository
from task_hub.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from task_hub.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, data: RegisterRequest) -> User:
        email = str(data.email)
        if await self.users.get_by_email(email):
            raise ConflictException(EMAIL_ALREADY_REGISTERED.format(email=email))
        try:
            user = await self.users.add(data, hash_password(data.password))
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictException(
                EMAIL_ALREADY_REGISTERED.format(email=email)
            ) from None
        await self.session.refresh(user)
        return user

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(str(data.email))
        if user is None or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedException(INVALID_CREDENTIALS)
        if not user.is_active:
            raise ForbiddenException(ACCOUNT_DEACTIVATED)
        refresh_token, jti, expires_at = create_refresh_token(user.id)
        await self.refresh_tokens.add(user.id, jti, expires_at)
        await self.session.commit()
        return TokenResponse(
            access_token=create_access_token(user.id), refresh_token=refresh_token
        )

    async def refresh(self, token: str) -> TokenResponse:
        payload = self._decode_refresh_token(token)
        jti = payload.get("jti")
        if not isinstance(jti, str):
            raise UnauthorizedException(INVALID_TOKEN)
        stored_token = await self.refresh_tokens.get_valid(jti)
        if stored_token is None:
            raise UnauthorizedException(TOKEN_REVOKED_OR_EXPIRED)
        user = await self.users.get_by_id(int(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedException(INVALID_TOKEN)

        await self.refresh_tokens.revoke(stored_token)
        new_refresh, new_jti, expires_at = create_refresh_token(user.id)
        await self.refresh_tokens.add(user.id, new_jti, expires_at)
        await self.session.commit()
        return TokenResponse(
            access_token=create_access_token(user.id), refresh_token=new_refresh
        )

    async def logout(self, token: str) -> None:
        payload = self._decode_refresh_token(token)
        jti = payload.get("jti")
        if not isinstance(jti, str):
            raise UnauthorizedException(INVALID_TOKEN)
        stored_token = await self.refresh_tokens.get_valid(jti)
        if stored_token is not None:
            await self.refresh_tokens.revoke(stored_token)
            await self.session.commit()

    @staticmethod
    def _decode_refresh_token(token: str) -> dict[str, Any]:
        try:
            payload = decode_token(token)
            if payload.get("type") != "refresh":
                raise UnauthorizedException(INVALID_TOKEN_TYPE)
            int(payload["sub"])
            return payload
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            raise UnauthorizedException(INVALID_TOKEN) from None
