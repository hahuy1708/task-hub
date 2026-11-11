from typing import Any

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

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
    TOKEN_REVOKED_OR_EXPIRED,
)
from task_hub.models.enums import TokenType
from task_hub.models.user import User
from task_hub.repositories.refresh_token import RefreshTokenRepository
from task_hub.repositories.user import UserRepository
from task_hub.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from task_hub.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_hash,
    verify_password,
)

DUMMY_PASSWORD_HASH = password_hash.hash("invalid-password")


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
            hashed_password = await run_in_threadpool(hash_password, data.password)
            user = await self.users.add(data, hashed_password)
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
        hashed_password = (
            user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
        )
        password_valid = await run_in_threadpool(
            verify_password, data.password, hashed_password
        )
        if user is None or not password_valid:
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
        user_id = int(payload["sub"])
        stored_token = await self.refresh_tokens.get_valid(jti)
        if stored_token is None:
            stored_token = await self.refresh_tokens.get_by_jti(jti)
            if stored_token is not None and stored_token.revoked_at is not None:
                await self.refresh_tokens.revoke_all_for_user(user_id)
                await self.session.commit()
            raise UnauthorizedException(TOKEN_REVOKED_OR_EXPIRED)
        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException(INVALID_TOKEN)

        if not await self.refresh_tokens.revoke(jti):
            await self.refresh_tokens.revoke_all_for_user(user_id)
            await self.session.commit()
            raise UnauthorizedException(TOKEN_REVOKED_OR_EXPIRED)
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
            if await self.refresh_tokens.revoke(jti):
                await self.session.commit()

    @staticmethod
    def _decode_refresh_token(token: str) -> dict[str, Any]:
        try:
            return decode_token(token, TokenType.REFRESH)
        except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
            raise UnauthorizedException(INVALID_TOKEN) from None
