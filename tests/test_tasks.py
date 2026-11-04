from collections.abc import Iterator
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from task_hub.main import app

API = "/api/v1/tasks"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def create_task(client: TestClient, title: str | None = None) -> dict[str, Any]:
    response = client.post(API, json={"title": title or f"Test {uuid4()}"})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_respects_pagination(client: TestClient) -> None:
    tasks = [create_task(client) for _ in range(3)]
    try:
        response = client.get(API, params={"limit": 2})
        assert response.status_code == 200
        assert len(response.json()) == 2
    finally:
        for task in tasks:
            client.delete(f"{API}/{task['id']}")


def test_create_get_update_and_delete(client: TestClient) -> None:
    task = create_task(client, "Persisted task")
    task_id = task["id"]

    response = client.get(f"{API}/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Persisted task"

    response = client.patch(f"{API}/{task_id}", json={"status": "DONE"})
    assert response.status_code == 200
    assert response.json()["status"] == "DONE"
    assert response.json()["title"] == "Persisted task"

    assert client.delete(f"{API}/{task_id}").status_code == 204
    assert client.get(f"{API}/{task_id}").status_code == 404


def test_task_remains_after_app_restart() -> None:
    title = f"Persistence check {uuid4()}"
    with TestClient(app) as first_client:
        created = create_task(first_client, title)
        task_id = created["id"]

    with TestClient(app) as second_client:
        response = second_client.get(f"{API}/{task_id}")
        assert response.status_code == 200
        assert response.json()["title"] == title
        assert second_client.delete(f"{API}/{task_id}").status_code == 204


def test_empty_title_is_rejected(client: TestClient) -> None:
    assert client.post(API, json={"title": ""}).status_code == 422


def test_task_id_must_be_positive(client: TestClient) -> None:
    assert client.get(f"{API}/0").status_code == 422


def test_missing_task_returns_404(client: TestClient) -> None:
    assert client.get(f"{API}/2147483000").status_code == 404
