from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from task_hub.models.user import User
from task_hub.schemas.auth import RegisterRequest


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.scalars(select(User).where(User.email == email))
        return result.first()

    async def add(self, data: RegisterRequest, hashed_password: str) -> User:
        user = User(
            email=str(data.email),
            full_name=data.full_name,
            hashed_password=hashed_password,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def save(self, user: User) -> User:
        await self.session.flush()
        return user

    async def list_all(self, *, skip: int, limit: int) -> list[User]:
        result = await self.session.scalars(
            select(User).order_by(User.id).offset(skip).limit(limit)
        )
        return list(result.all())
