import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from task_hub.core.config import settings
from task_hub.models.enums import TokenType

password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    return password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)


def _encode(user_id: int, token_type: TokenType, expires_at: datetime, jti: str) -> str:
    return jwt.encode(
        {"sub": str(user_id), "type": token_type, "jti": jti, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return _encode(user_id, TokenType.ACCESS, expires_at, uuid.uuid4().hex)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    jti = uuid.uuid4().hex
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return _encode(user_id, TokenType.REFRESH, expires_at, jti), jti, expires_at


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type")
    int(payload["sub"])
    return payload
