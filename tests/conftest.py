import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///unused.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")

from task_hub.models import Base, SystemRole, User


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///unused.db")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    from task_hub.dependencies import get_session
    from task_hub.main import app

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
        app.state.test_session_factory = session_factory

        async def override_get_session() -> AsyncIterator[AsyncSession]:
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        try:
            with TestClient(app) as test_client:
                yield test_client
        finally:
            app.dependency_overrides.pop(get_session, None)
            del app.state.test_session_factory
            asyncio.run(test_engine.dispose())


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    email = f"{uuid4()}@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": "password123"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200
    client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    return client


@pytest.fixture
def admin_client(authenticated_client: TestClient) -> TestClient:
    from task_hub.main import app

    user_id = authenticated_client.get("/api/v1/users/me").json()["id"]
    session_factory = app.state.test_session_factory

    async def promote_user() -> None:
        async with session_factory() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(role=SystemRole.ADMIN)
            )
            await session.commit()

    portal = authenticated_client.portal
    assert portal is not None
    portal.call(promote_user)
    return authenticated_client
