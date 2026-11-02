from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from task_hub.dependencies import get_task_service
from task_hub.main import app
from task_hub.services.task import TaskService

API = "/api/v1/tasks"


@pytest.fixture
def client() -> Iterator[TestClient]:
    service = TaskService()
    app.dependency_overrides[get_task_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_returns_seed_data(client: TestClient) -> None:
    assert len(client.get(API).json()) == 3


def test_list_respects_limit(client: TestClient) -> None:
    assert len(client.get(API, params={"limit": 2}).json()) == 2


def test_create_then_get(client: TestClient) -> None:
    created = client.post(API, json={"title": "Viết test"})
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert client.get(f"{API}/{task_id}").json()["title"] == "Viết test"


def test_empty_title_is_rejected(client: TestClient) -> None:
    assert client.post(API, json={"title": ""}).status_code == 422


def test_task_id_must_be_positive(client: TestClient) -> None:
    assert client.get(f"{API}/0").status_code == 422


def test_missing_task_returns_404(client: TestClient) -> None:
    assert client.get(f"{API}/999").status_code == 404


def test_patch_changes_only_sent_fields(client: TestClient) -> None:
    response = client.patch(f"{API}/1", json={"status": "DONE"})
    assert response.json()["status"] == "DONE"
    assert response.json()["title"] == "Thiết kế DB schema"


def test_delete_then_404(client: TestClient) -> None:
    assert client.delete(f"{API}/1").status_code == 204
    assert client.get(f"{API}/1").status_code == 404
