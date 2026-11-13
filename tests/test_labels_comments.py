from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient

AUTH = "/api/v1/auth"
WORKSPACES = "/api/v1/workspaces"
PROJECTS = "/api/v1/projects"
TASKS = "/api/v1/tasks"


def make_user(client: TestClient, name: str = "Feature User") -> dict[str, str]:
    email = f"{uuid4()}@example.com"
    password = "password123"
    assert (
        client.post(
            f"{AUTH}/register",
            json={"email": email, "full_name": name, "password": password},
        ).status_code
        == 201
    )
    response = client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_project(client: TestClient, headers: dict[str, str]) -> tuple[int, int]:
    workspace = client.post(
        WORKSPACES, headers=headers, json={"name": f"Workspace {uuid4()}"}
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]
    project = client.post(
        f"{WORKSPACES}/{workspace_id}/projects",
        headers=headers,
        json={"name": f"Project {uuid4()}"},
    )
    assert project.status_code == 201
    return workspace_id, project.json()["id"]


def add_member(
    client: TestClient,
    workspace_id: int,
    owner: dict[str, str],
    member: dict[str, str],
    role: str,
) -> None:
    user_id = client.get("/api/v1/users/me", headers=member).json()["id"]
    response = client.post(
        f"{WORKSPACES}/{workspace_id}/members",
        headers=owner,
        json={"user_id": user_id, "role": role},
    )
    assert response.status_code == 201


def create_task(
    client: TestClient, project_id: int, headers: dict[str, str]
) -> dict[str, Any]:
    response = client.post(
        f"{PROJECTS}/{project_id}/tasks",
        headers=headers,
        json={"title": f"Task {uuid4()}"},
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_labels_are_project_scoped_and_included_in_task_read(
    authenticated_client: TestClient,
) -> None:
    _, project_id = create_project(authenticated_client, {})
    _, other_project_id = create_project(authenticated_client, {})
    task = create_task(authenticated_client, project_id, {})
    label = authenticated_client.post(
        f"{PROJECTS}/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
    )
    assert label.status_code == 201
    label_id = label.json()["id"]
    assert (
        authenticated_client.post(f"{TASKS}/{task['id']}/labels/{label_id}").status_code
        == 204
    )
    task_read = authenticated_client.get(f"{TASKS}/{task['id']}")
    assert task_read.status_code == 200
    assert task_read.json()["labels"] == [label.json()]

    other_label = authenticated_client.post(
        f"{PROJECTS}/{other_project_id}/labels",
        json={"name": "other", "color": "#000000"},
    )
    assert other_label.status_code == 201
    assert (
        authenticated_client.post(
            f"{TASKS}/{task['id']}/labels/{other_label.json()['id']}"
        ).status_code
        == 422
    )
    assert (
        authenticated_client.post(
            f"{PROJECTS}/{project_id}/labels",
            json={"name": "bug", "color": "#ffffff"},
        ).status_code
        == 409
    )


def test_label_and_comment_permissions(client: TestClient) -> None:
    owner = make_user(client, "Owner")
    editor = make_user(client, "Editor")
    viewer = make_user(client, "Viewer")
    workspace_id, project_id = create_project(client, owner)
    add_member(client, workspace_id, owner, editor, "EDITOR")
    add_member(client, workspace_id, owner, viewer, "VIEWER")
    task = create_task(client, project_id, editor)

    assert (
        client.post(
            f"{PROJECTS}/{project_id}/labels",
            headers=viewer,
            json={"name": "denied", "color": "#000000"},
        ).status_code
        == 403
    )
    comment = client.post(
        f"{TASKS}/{task['id']}/comments",
        headers=editor,
        json={"content": "Looks good"},
    )
    assert comment.status_code == 201
    comment_id = comment.json()["id"]
    assert (
        client.get(f"{TASKS}/{task['id']}/comments", headers=viewer).status_code == 200
    )
    assert (
        client.delete(f"/api/v1/comments/{comment_id}", headers=viewer).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/comments/{comment_id}", headers=owner).status_code
        == 204
    )


def test_fakeredis_ping() -> None:
    import asyncio

    import fakeredis.aioredis

    async def ping() -> bool:
        redis = fakeredis.aioredis.FakeRedis()
        try:
            return bool(await redis.ping())
        finally:
            await redis.aclose()

    assert asyncio.run(ping())
