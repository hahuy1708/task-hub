import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from task_hub.dependencies import get_session
from task_hub.main import app
from task_hub.models import Base


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TemporaryDirectory(prefix=".taskhub-test-", dir=Path.cwd()) as temp_dir:
        database_path = (Path(temp_dir) / "test.db").as_posix()
        test_engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}", poolclass=NullPool
        )

        async def create_tables() -> None:
            async with test_engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

        asyncio.run(create_tables())
        session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

        async def override_get_session() -> AsyncIterator[AsyncSession]:
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        try:
            with TestClient(app) as test_client:
                yield test_client
        finally:
            app.dependency_overrides.pop(get_session, None)
            asyncio.run(test_engine.dispose())
