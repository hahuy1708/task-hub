from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.core.exceptions import UnauthorizedException
from task_hub.core.messages import WRONG_CURRENT_PASSWORD
from task_hub.models.user import User
from task_hub.repositories.refresh_token import RefreshTokenRepository
from task_hub.repositories.user import UserRepository
from task_hub.schemas.user import ChangePasswordRequest, UserUpdate
from task_hub.security import hash_password, verify_password


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def update_me(self, user: User, data: UserUpdate) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        await self.users.save(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedException(WRONG_CURRENT_PASSWORD)
        user.hashed_password = hash_password(data.new_password)
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.session.commit()
