from uuid import uuid4

from fastapi.testclient import TestClient

AUTH = "/api/v1/auth"
WORKSPACES = "/api/v1/workspaces"
PROJECTS = "/api/v1/projects"


def make_user(client: TestClient) -> dict[str, str]:
    email = f"{uuid4()}@example.com"
    password = "password123"
    assert (
        client.post(
            f"{AUTH}/register",
            json={"email": email, "full_name": "Project User", "password": password},
        ).status_code
        == 201
    )
    response = client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_member(
    client: TestClient,
    workspace_id: int,
    owner_headers: dict[str, str],
    member_headers: dict[str, str],
    role: str,
) -> None:
    user_id = client.get("/api/v1/users/me", headers=member_headers).json()["id"]
    response = client.post(
        f"{WORKSPACES}/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": user_id, "role": role},
    )
    assert response.status_code == 201


def test_project_role_permissions_and_archive(client: TestClient) -> None:
    owner_headers = make_user(client)
    editor_headers = make_user(client)
    viewer_headers = make_user(client)
    outsider_headers = make_user(client)
    workspace_response = client.post(
        WORKSPACES, headers=owner_headers, json={"name": "Project workspace"}
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["id"]
    add_member(client, workspace_id, owner_headers, editor_headers, "EDITOR")
    add_member(client, workspace_id, owner_headers, viewer_headers, "VIEWER")

    create_url = f"{WORKSPACES}/{workspace_id}/projects"
    project_response = client.post(
        create_url,
        headers=editor_headers,
        json={"name": "API", "description": "First version"},
    )
    assert project_response.status_code == 201
    project = project_response.json()
    project_url = f"{PROJECTS}/{project['id']}"

    assert (
        client.post(
            create_url, headers=viewer_headers, json={"name": "Denied"}
        ).status_code
        == 403
    )
    assert client.get(project_url, headers=viewer_headers).status_code == 200
    archived = client.patch(
        project_url,
        headers=editor_headers,
        json={"status": "ARCHIVED", "description": None},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["description"] is None
    assert (
        client.patch(
            project_url, headers=viewer_headers, json={"name": "Denied"}
        ).status_code
        == 403
    )
    assert client.delete(project_url, headers=editor_headers).status_code == 403
    assert client.get(project_url, headers=outsider_headers).status_code == 403

    filtered = client.get(
        create_url,
        headers=viewer_headers,
        params={"status": "ARCHIVED", "skip": 0, "limit": 10},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert [item["id"] for item in filtered.json()["items"]] == [project["id"]]
    assert client.delete(project_url, headers=owner_headers).status_code == 204
    assert client.get(project_url, headers=owner_headers).status_code == 404
