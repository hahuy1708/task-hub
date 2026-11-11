from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient

AUTH = "/api/v1/auth"
WORKSPACES = "/api/v1/workspaces"


def make_user(client: TestClient) -> dict[str, str]:
    email = f"{uuid4()}@example.com"
    password = "password123"
    registered = client.post(
        f"{AUTH}/register",
        json={"email": email, "full_name": "Workspace User", "password": password},
    )
    assert registered.status_code == 201
    response = client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_workspace(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(WORKSPACES, headers=headers, json={"name": "Team space"})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_create_and_list_workspaces(client: TestClient) -> None:
    owner_headers = make_user(client)
    outsider_headers = make_user(client)
    workspace = create_workspace(client, owner_headers)

    members = client.get(
        f"{WORKSPACES}/{workspace['id']}/members", headers=owner_headers
    )
    assert members.status_code == 200
    assert members.json()[0]["role"] == "OWNER"
    assert members.json()[0]["user_id"] == workspace["owner_id"]
    listed = client.get(WORKSPACES, headers=outsider_headers).json()
    assert listed == {"items": [], "total": 0}
    assert (
        client.get(
            f"{WORKSPACES}/{workspace['id']}", headers=outsider_headers
        ).status_code
        == 403
    )


def test_workspace_owner_permissions_and_delete(client: TestClient) -> None:
    owner_headers = make_user(client)
    member_headers = make_user(client)
    workspace = create_workspace(client, owner_headers)
    workspace_id = workspace["id"]

    added = client.post(
        f"{WORKSPACES}/{workspace_id}/members",
        headers=owner_headers,
        json={
            "user_id": int(
                client.get("/api/v1/users/me", headers=member_headers).json()["id"]
            ),
            "role": "EDITOR",
        },
    )
    assert added.status_code == 201
    assert (
        client.patch(
            f"{WORKSPACES}/{workspace_id}",
            headers=member_headers,
            json={"name": "Not allowed"},
        ).status_code
        == 403
    )
    renamed = client.patch(
        f"{WORKSPACES}/{workspace_id}",
        headers=owner_headers,
        json={"name": "Renamed"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"
    assert (
        client.delete(
            f"{WORKSPACES}/{workspace_id}", headers=member_headers
        ).status_code
        == 403
    )
    assert (
        client.delete(f"{WORKSPACES}/{workspace_id}", headers=owner_headers).status_code
        == 204
    )
    assert (
        client.get(f"{WORKSPACES}/{workspace_id}", headers=owner_headers).status_code
        == 404
    )


def test_owner_adds_member_and_member_can_leave(client: TestClient) -> None:
    owner_headers = make_user(client)
    member_headers = make_user(client)
    owner_id = client.get("/api/v1/users/me", headers=owner_headers).json()["id"]
    member_id = client.get("/api/v1/users/me", headers=member_headers).json()["id"]
    workspace = create_workspace(client, owner_headers)
    workspace_id = workspace["id"]

    assert (
        client.post(
            f"{WORKSPACES}/{workspace_id}/members",
            headers=owner_headers,
            json={"user_id": member_id, "role": "VIEWER"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{WORKSPACES}/{workspace_id}/members",
            headers=owner_headers,
            json={"user_id": member_id, "role": "EDITOR"},
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"{WORKSPACES}/{workspace_id}/members/{owner_id}", headers=owner_headers
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"{WORKSPACES}/{workspace_id}/members/{member_id}", headers=member_headers
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"{WORKSPACES}/{workspace_id}/members", headers=member_headers
        ).status_code
        == 403
    )


def test_cannot_add_member_with_owner_role(client: TestClient) -> None:
    owner_headers = make_user(client)
    member_headers = make_user(client)
    member_id = client.get("/api/v1/users/me", headers=member_headers).json()["id"]
    workspace = create_workspace(client, owner_headers)

    response = client.post(
        f"{WORKSPACES}/{workspace['id']}/members",
        headers=owner_headers,
        json={"user_id": member_id, "role": "OWNER"},
    )
    assert response.status_code == 422


def test_admin_can_access_and_delete_other_user_workspace(
    admin_client: TestClient,
) -> None:
    owner_headers = make_user(admin_client)
    workspace = create_workspace(admin_client, owner_headers)
    workspace_id = workspace["id"]

    workspaces_list = admin_client.get(WORKSPACES).json()
    assert any(ws["id"] == workspace_id for ws in workspaces_list["items"])

    response = admin_client.get(f"{WORKSPACES}/{workspace_id}")
    assert response.status_code == 200
    assert response.json()["id"] == workspace_id

    delete_response = admin_client.delete(f"{WORKSPACES}/{workspace_id}")
    assert delete_response.status_code == 204
    assert admin_client.get(f"{WORKSPACES}/{workspace_id}").status_code == 404
