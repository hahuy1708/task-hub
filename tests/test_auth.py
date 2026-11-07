from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient

AUTH = "/api/v1/auth"
USERS = "/api/v1/users"


def register(client: TestClient) -> tuple[str, str]:
    email = f"{uuid4()}@example.com"
    response = client.post(
        f"{AUTH}/register",
        json={"email": email, "full_name": "Test User", "password": "password123"},
    )
    assert response.status_code == 201
    assert "hashed_password" not in response.json()
    return email, "password123"


def login(client: TestClient, email: str, password: str) -> dict[str, Any]:
    response = client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    email, password = register(client)
    duplicate = client.post(
        f"{AUTH}/register",
        json={"email": email, "full_name": "Another User", "password": password},
    )
    assert duplicate.status_code == 409


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        f"{AUTH}/login",
        json={"email": "unknown@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_login_and_get_current_user(client: TestClient) -> None:
    email, password = register(client)
    tokens = login(client, email, password)
    response = client.get(
        f"{USERS}/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["role"] == "MEMBER"


def test_refresh_rotates_and_logout_revokes_token(client: TestClient) -> None:
    email, password = register(client)
    tokens = login(client, email, password)

    refreshed = client.post(
        f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    old_refresh = client.post(
        f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert old_refresh.status_code == 401

    assert (
        client.post(
            f"{AUTH}/logout", json={"refresh_token": new_tokens["refresh_token"]}
        ).status_code
        == 204
    )
    assert (
        client.post(
            f"{AUTH}/logout", json={"refresh_token": new_tokens["refresh_token"]}
        ).status_code
        == 204
    )


def test_change_password_revokes_refresh_tokens(client: TestClient) -> None:
    email, password = register(client)
    tokens = login(client, email, password)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    changed = client.post(
        f"{USERS}/me/change-password",
        headers=headers,
        json={"current_password": password, "new_password": "newpassword123"},
    )
    assert changed.status_code == 204
    revoked = client.post(
        f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert revoked.status_code == 401
    assert login(client, email, "newpassword123")["access_token"]


def test_member_cannot_list_users(authenticated_client: TestClient) -> None:
    assert authenticated_client.get(USERS).status_code == 403


def test_admin_can_list_users(admin_client: TestClient) -> None:
    response = admin_client.get(USERS)
    assert response.status_code == 200
    assert response.json()[0]["role"] == "ADMIN"
