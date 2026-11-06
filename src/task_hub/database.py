from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from task_hub.core.config import settings

DATABASE_URL = settings.database_url

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
