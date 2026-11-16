from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis

from task_hub.main import app
from task_hub.models.task import Task
from task_hub.repositories.task import TaskRepository

API = "/api/v1"


@pytest.fixture
def repo_calls(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []
    original = TaskRepository.list_by_project

    async def counting(
        self: TaskRepository, *args: Any, **kwargs: Any
    ) -> tuple[list[Task], int]:
        calls.append(1)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(TaskRepository, "list_by_project", counting)
    return calls


def create_project(client: TestClient) -> int:
    workspace = client.post(f"{API}/workspaces", json={"name": "Cache"})
    assert workspace.status_code == 201
    project = client.post(
        f"{API}/workspaces/{workspace.json()['id']}/projects", json={"name": "P"}
    )
    assert project.status_code == 201
    return int(project.json()["id"])


def create_task(client: TestClient, project_id: int, title: str = "Task") -> int:
    response = client.post(f"{API}/projects/{project_id}/tasks", json={"title": title})
    assert response.status_code == 201
    return int(response.json()["id"])


def list_tasks(client: TestClient, project_id: int, **params: str) -> dict[str, Any]:
    response = client.get(f"{API}/projects/{project_id}/tasks", params=params)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def label_names(client: TestClient, project_id: int) -> list[str]:
    items = list_tasks(client, project_id)["items"]
    return [label["name"] for label in items[0]["labels"]]


def register_headers(client: TestClient) -> dict[str, str]:
    email = f"{uuid4()}@example.com"
    password = "password123"
    registered = client.post(
        f"{API}/auth/register",
        json={"email": email, "full_name": "Other", "password": password},
    )
    assert registered.status_code == 201
    token = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_task_list_is_served_from_cache_until_tasks_change(
    authenticated_client: TestClient, repo_calls: list[int]
) -> None:
    client = authenticated_client
    project_id = create_project(client)
    task_id = create_task(client, project_id, "First")

    first = list_tasks(client, project_id)
    assert first["total"] == 1
    assert len(repo_calls) == 1

    assert list_tasks(client, project_id) == first
    assert len(repo_calls) == 1

    client.patch(f"{API}/tasks/{task_id}", json={"status": "DONE"})
    updated = list_tasks(client, project_id)
    assert updated["items"][0]["status"] == "DONE"
    assert len(repo_calls) == 2

    create_task(client, project_id, "Second")
    assert list_tasks(client, project_id)["total"] == 2
    assert len(repo_calls) == 3


def test_filters_and_pagination_use_separate_cache_entries(
    authenticated_client: TestClient, repo_calls: list[int]
) -> None:
    client = authenticated_client
    project_id = create_project(client)
    create_task(client, project_id)

    list_tasks(client, project_id)
    list_tasks(client, project_id, status="DONE")
    assert len(repo_calls) == 2

    list_tasks(client, project_id)
    list_tasks(client, project_id, status="DONE")
    assert len(repo_calls) == 2


def test_label_changes_refresh_cached_task_labels(
    authenticated_client: TestClient,
) -> None:
    client = authenticated_client
    project_id = create_project(client)
    task_id = create_task(client, project_id)
    label = client.post(
        f"{API}/projects/{project_id}/labels", json={"name": "bug", "color": "red"}
    ).json()
    label_id = label["id"]

    assert client.post(f"{API}/tasks/{task_id}/labels/{label_id}").status_code == 204
    names = label_names(client, project_id)
    assert names == ["bug"]

    assert (
        client.patch(f"{API}/labels/{label_id}", json={"name": "defect"}).status_code
        == 200
    )
    names = label_names(client, project_id)
    assert names == ["defect"]

    assert client.delete(f"{API}/tasks/{task_id}/labels/{label_id}").status_code == 204
    assert list_tasks(client, project_id)["items"][0]["labels"] == []


def test_cached_list_still_checks_workspace_access(
    authenticated_client: TestClient,
) -> None:
    client = authenticated_client
    project_id = create_project(client)
    create_task(client, project_id)
    assert list_tasks(client, project_id)["total"] == 1

    outsider = register_headers(client)
    response = client.get(f"{API}/projects/{project_id}/tasks", headers=outsider)
    assert response.status_code == 403


def test_redis_outage_falls_back_to_database(
    authenticated_client: TestClient,
) -> None:
    client = authenticated_client
    project_id = create_project(client)
    create_task(client, project_id, "Still readable")

    app.state.redis = Redis.from_url(
        "redis://127.0.0.1:1/0", decode_responses=True, socket_connect_timeout=0.2
    )

    assert list_tasks(client, project_id)["total"] == 1
    created = client.post(
        f"{API}/projects/{project_id}/tasks", json={"title": "Written"}
    )
    assert created.status_code == 201
    assert list_tasks(client, project_id)["total"] == 2
