import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

API = "/api/v1"
LOGGER_NAME = "task_hub.notifications"


def register(client: TestClient) -> tuple[dict[str, str], int, str]:
    email = f"{uuid4()}@example.com"
    password = "password123"
    registered = client.post(
        f"{API}/auth/register",
        json={"email": email, "full_name": "Member", "password": password},
    )
    assert registered.status_code == 201
    token = client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = int(client.get(f"{API}/users/me", headers=headers).json()["id"])
    return headers, user_id, email


def assignment_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == LOGGER_NAME]


def test_assignment_notifies_only_when_a_new_person_is_assigned(
    authenticated_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    client = authenticated_client
    _, member_id, member_email = register(client)
    owner_id = int(client.get(f"{API}/users/me").json()["id"])

    workspace_id = client.post(f"{API}/workspaces", json={"name": "Notify"}).json()[
        "id"
    ]
    project_id = client.post(
        f"{API}/workspaces/{workspace_id}/projects", json={"name": "P"}
    ).json()["id"]
    added = client.post(
        f"{API}/workspaces/{workspace_id}/members",
        json={"user_id": member_id, "role": "EDITOR"},
    )
    assert added.status_code == 201

    created = client.post(
        f"{API}/projects/{project_id}/tasks",
        json={"title": "Ship", "assignee_id": member_id},
    )
    assert created.status_code == 201
    task_id = created.json()["id"]
    records = assignment_records(caplog)
    assert len(records) == 1
    assert records[0].getMessage() == (
        f"Task assigned email to={member_email} task_id={task_id} title=Ship"
    )

    # Gán lại cùng người và đổi trạng thái: không gửi thêm thư.
    client.patch(
        f"{API}/tasks/{task_id}",
        json={"assignee_id": member_id, "status": "IN_PROGRESS"},
    )
    assert len(assignment_records(caplog)) == 1

    # Gán cho chính người thao tác: không gửi thư.
    client.patch(f"{API}/tasks/{task_id}", json={"assignee_id": owner_id})
    assert len(assignment_records(caplog)) == 1

    # Gán lại cho thành viên sau khi đã đổi người: gửi thêm một lần.
    client.patch(f"{API}/tasks/{task_id}", json={"assignee_id": member_id})
    assert len(assignment_records(caplog)) == 2
