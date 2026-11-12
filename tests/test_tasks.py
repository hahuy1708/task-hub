from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient

AUTH = "/api/v1/auth"
PROJECTS = "/api/v1/projects"
TASKS = "/api/v1/tasks"
WORKSPACES = "/api/v1/workspaces"


def make_user(client: TestClient) -> dict[str, str]:
    email = f"{uuid4()}@example.com"
    password = "password123"
    response = client.post(
        f"{AUTH}/register",
        json={"email": email, "full_name": "Task User", "password": password},
    )
    assert response.status_code == 201
    response = client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_project(client: TestClient, headers: dict[str, str]) -> tuple[int, int]:
    workspace_response = client.post(
        WORKSPACES, headers=headers, json={"name": "Task workspace"}
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]
    project_response = client.post(
        f"{WORKSPACES}/{workspace_id}/projects",
        headers=headers,
        json={"name": "Task project"},
    )
    assert project_response.status_code == 201
    return workspace_id, project_response.json()["id"]


def add_member(
    client: TestClient,
    workspace_id: int,
    owner_headers: dict[str, str],
    member_headers: dict[str, str],
    role: str,
) -> int:
    member_id = cast(
        int, client.get("/api/v1/users/me", headers=member_headers).json()["id"]
    )
    response = client.post(
        f"{WORKSPACES}/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": member_id, "role": role},
    )
    assert response.status_code == 201
    return member_id


def create_task(
    client: TestClient,
    project_id: int,
    headers: dict[str, str],
    **data: Any,
) -> dict[str, Any]:
    response = client.post(
        f"{PROJECTS}/{project_id}/tasks",
        headers=headers,
        json={"title": f"Task {uuid4()}", **data},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_project_task_crud_and_pagination(authenticated_client: TestClient) -> None:
    _, project_id = create_project(authenticated_client, {})
    created = [create_task(authenticated_client, project_id, {}) for _ in range(3)]

    response = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks", params={"limit": 2}
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["total"] == 3
    task_id = created[0]["id"]
    response = authenticated_client.get(f"{TASKS}/{task_id}")
    assert response.status_code == 200
    assert response.json()["project_id"] == project_id
    assert response.json()["created_by"] is not None

    response = authenticated_client.patch(f"{TASKS}/{task_id}", json={"status": "DONE"})
    assert response.status_code == 200
    assert response.json()["status"] == "DONE"
    assert authenticated_client.delete(f"{TASKS}/{task_id}").status_code == 204
    assert authenticated_client.get(f"{TASKS}/{task_id}").status_code == 404


def test_task_access_uses_workspace_roles(client: TestClient) -> None:
    owner = make_user(client)
    editor = make_user(client)
    viewer = make_user(client)
    outsider = make_user(client)
    workspace_id, project_id = create_project(client, owner)
    add_member(client, workspace_id, owner, editor, "EDITOR")
    add_member(client, workspace_id, owner, viewer, "VIEWER")
    task = create_task(client, project_id, editor)
    task_url = f"{TASKS}/{task['id']}"
    collection_url = f"{PROJECTS}/{project_id}/tasks"

    assert client.get(collection_url, headers=viewer).status_code == 200
    assert client.get(task_url, headers=viewer).status_code == 200
    assert (
        client.post(
            collection_url, headers=viewer, json={"title": "Denied"}
        ).status_code
        == 403
    )
    assert (
        client.patch(task_url, headers=viewer, json={"title": "Denied"}).status_code
        == 403
    )
    assert client.delete(task_url, headers=viewer).status_code == 403

    assert client.get(collection_url, headers=outsider).status_code == 403
    assert (
        client.post(
            collection_url, headers=outsider, json={"title": "Denied"}
        ).status_code
        == 403
    )
    assert client.get(task_url, headers=outsider).status_code == 403
    assert (
        client.patch(task_url, headers=outsider, json={"title": "Denied"}).status_code
        == 403
    )
    assert client.delete(task_url, headers=outsider).status_code == 403


def test_admin_bypasses_workspace_membership(admin_client: TestClient) -> None:
    owner = make_user(admin_client)
    _, project_id = create_project(admin_client, owner)
    task = create_task(admin_client, project_id, owner)

    assert admin_client.get(f"{TASKS}/{task['id']}").status_code == 200
    response = admin_client.post(
        f"{PROJECTS}/{project_id}/tasks", json={"title": "Created by admin"}
    )
    assert response.status_code == 201


def test_filters_combine_and_total_counts_filtered_tasks(
    authenticated_client: TestClient,
) -> None:
    workspace_id, project_id = create_project(authenticated_client, {})
    assignee = make_user(authenticated_client)
    assignee_id = add_member(authenticated_client, workspace_id, {}, assignee, "EDITOR")
    matching = create_task(
        authenticated_client,
        project_id,
        {},
        title="matching",
        priority="HIGH",
        assignee_id=assignee_id,
    )
    create_task(
        authenticated_client,
        project_id,
        {},
        title="wrong status",
        priority="HIGH",
        assignee_id=assignee_id,
    )
    create_task(
        authenticated_client,
        project_id,
        {},
        title="wrong priority",
        priority="LOW",
        assignee_id=assignee_id,
    )
    create_task(
        authenticated_client,
        project_id,
        {},
        title="wrong assignee",
        priority="HIGH",
    )
    response = authenticated_client.patch(
        f"{TASKS}/{matching['id']}", json={"status": "DONE"}
    )
    assert response.status_code == 200
    wrong_priority = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks", params={"priority": "LOW"}
    )
    wrong_priority_id = wrong_priority.json()["items"][0]["id"]
    wrong_assignee_id = next(
        item["id"]
        for item in authenticated_client.get(
            f"{PROJECTS}/{project_id}/tasks", params={"priority": "HIGH"}
        ).json()["items"]
        if item["title"] == "wrong assignee"
    )
    for task_id in (wrong_priority_id, wrong_assignee_id):
        response = authenticated_client.patch(
            f"{TASKS}/{task_id}", json={"status": "DONE"}
        )
        assert response.status_code == 200

    response = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks",
        params={
            "status": "DONE",
            "priority": "HIGH",
            "assignee_id": assignee_id,
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [matching["id"]]

    priority_page = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks", params={"priority": "HIGH", "limit": 1}
    )
    assert len(priority_page.json()["items"]) == 1
    assert priority_page.json()["total"] == 3

    status_page = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks", params={"status": "TODO"}
    )
    assert status_page.json()["total"] == 1
    assignee_page = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks", params={"assignee_id": assignee_id}
    )
    assert assignee_page.json()["total"] == 3
    paged = authenticated_client.get(
        f"{PROJECTS}/{project_id}/tasks", params={"skip": 1, "limit": 2}
    )
    assert len(paged.json()["items"]) == 2
    assert paged.json()["total"] == 4


def test_assignee_must_belong_to_project_workspace(client: TestClient) -> None:
    owner = make_user(client)
    outsider = make_user(client)
    workspace_id, project_id = create_project(client, owner)
    outsider_id = client.get("/api/v1/users/me", headers=outsider).json()["id"]
    collection_url = f"{PROJECTS}/{project_id}/tasks"

    response = client.post(
        collection_url,
        headers=owner,
        json={"title": "Invalid assignment", "assignee_id": outsider_id},
    )
    assert response.status_code == 422

    member = make_user(client)
    member_id = add_member(client, workspace_id, owner, member, "VIEWER")
    task = create_task(client, project_id, owner)
    assert (
        client.patch(
            f"{TASKS}/{task['id']}", json={"assignee_id": member_id}, headers=owner
        ).status_code
        == 200
    )
    rejected = client.patch(
        f"{TASKS}/{task['id']}", json={"assignee_id": outsider_id}, headers=owner
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]


def test_archived_project_blocks_task_create_and_update(
    authenticated_client: TestClient,
) -> None:
    _, project_id = create_project(authenticated_client, {})
    task = create_task(authenticated_client, project_id, {})
    archived = authenticated_client.patch(
        f"{PROJECTS}/{project_id}", json={"status": "ARCHIVED"}
    )
    assert archived.status_code == 200
    assert (
        authenticated_client.post(
            f"{PROJECTS}/{project_id}/tasks", json={"title": "Blocked"}
        ).status_code
        == 409
    )
    assert (
        authenticated_client.patch(
            f"{TASKS}/{task['id']}", json={"title": "Blocked"}
        ).status_code
        == 409
    )
    assert authenticated_client.delete(f"{TASKS}/{task['id']}").status_code == 204


def test_deleting_project_removes_its_tasks(authenticated_client: TestClient) -> None:
    _, project_id = create_project(authenticated_client, {})
    task = create_task(authenticated_client, project_id, {})

    assert authenticated_client.delete(f"{PROJECTS}/{project_id}").status_code == 204
    assert authenticated_client.get(f"{TASKS}/{task['id']}").status_code == 404


def test_due_date_cannot_be_in_the_past(authenticated_client: TestClient) -> None:
    _, project_id = create_project(authenticated_client, {})
    response = authenticated_client.post(
        f"{PROJECTS}/{project_id}/tasks",
        json={
            "title": "Past due",
            "due_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 422


def test_patch_rejects_null_required_fields_and_clears_nullable_fields(
    authenticated_client: TestClient,
) -> None:
    _, project_id = create_project(authenticated_client, {})
    task = create_task(
        authenticated_client,
        project_id,
        {},
        title="Nullable test",
        description="Clear me",
        due_date=(date.today() + timedelta(days=1)).isoformat(),
    )
    task_url = f"{TASKS}/{task['id']}"
    assert authenticated_client.patch(task_url, json={"title": None}).status_code == 422
    cleared = authenticated_client.patch(
        task_url, json={"description": None, "due_date": None, "assignee_id": None}
    )
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["due_date"] is None
    assert cleared.json()["assignee_id"] is None


def test_created_at_is_utc(authenticated_client: TestClient) -> None:
    _, project_id = create_project(authenticated_client, {})
    task = create_task(authenticated_client, project_id, {})
    created_at = task["created_at"].replace("Z", "+00:00")
    assert datetime.fromisoformat(created_at).utcoffset() == timedelta(0)


def test_flat_task_collection_is_removed(
    authenticated_client: TestClient,
) -> None:
    assert authenticated_client.get(TASKS).status_code == 404
    assert (
        authenticated_client.post(TASKS, json={"title": "Old route"}).status_code == 404
    )


def test_task_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/projects/1/tasks").status_code == 401
    assert client.get(f"{TASKS}/1").status_code == 401
