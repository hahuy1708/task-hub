from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    AsyncTransaction,
    create_async_engine,
)

from task_hub.core.config import settings
from task_hub.dependencies import get_session
from task_hub.main import app
from task_hub.models import Task


@pytest.fixture
def client() -> Iterator[TestClient]:
    test_database_url = settings.test_database_url
    if not test_database_url:
        pytest.fail("Set TEST_DATABASE_URL in .env to a separate test database")
    if test_database_url == settings.database_url:
        pytest.fail("TEST_DATABASE_URL must not point to the development database")

    test_engine = create_async_engine(test_database_url, pool_pre_ping=True)
    connection: AsyncConnection | None = None

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        assert connection is not None
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    async def begin_test_transaction() -> tuple[AsyncConnection, AsyncTransaction]:
        test_connection = await test_engine.connect()
        transaction = await test_connection.begin()
        await test_connection.execute(delete(Task))
        return test_connection, transaction

    async def rollback_test_data(
        test_connection: AsyncConnection, transaction: AsyncTransaction
    ) -> None:
        await transaction.rollback()
        await test_connection.close()
        await test_engine.dispose()

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            portal = test_client.portal
            assert portal is not None
            connection, transaction = portal.call(begin_test_transaction)
            try:
                yield test_client
            finally:
                portal.call(rollback_test_data, connection, transaction)
    finally:
        app.dependency_overrides.pop(get_session, None)
