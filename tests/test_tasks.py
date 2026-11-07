from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient

API = "/api/v1/tasks"


def create_task(client: TestClient, title: str | None = None) -> dict[str, Any]:
    response = client.post(API, json={"title": title or f"Test {uuid4()}"})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_respects_pagination(authenticated_client: TestClient) -> None:
    for _ in range(3):
        create_task(authenticated_client)

    response = authenticated_client.get(API, params={"limit": 2})
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.headers["X-Total-Count"] == "3"


def test_create_get_update_and_delete(authenticated_client: TestClient) -> None:
    task = create_task(authenticated_client, "Persisted task")
    task_id = task["id"]

    response = authenticated_client.get(f"{API}/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Persisted task"

    response = authenticated_client.patch(f"{API}/{task_id}", json={"status": "DONE"})
    assert response.status_code == 200
    assert response.json()["status"] == "DONE"
    assert response.json()["title"] == "Persisted task"

    assert authenticated_client.delete(f"{API}/{task_id}").status_code == 204
    assert authenticated_client.get(f"{API}/{task_id}").status_code == 404


def test_task_is_available_to_later_requests(authenticated_client: TestClient) -> None:
    title = f"Persistence check {uuid4()}"
    created = create_task(authenticated_client, title)
    response = authenticated_client.get(f"{API}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == title


def test_empty_title_is_rejected(authenticated_client: TestClient) -> None:
    assert authenticated_client.post(API, json={"title": ""}).status_code == 422


def test_task_id_must_be_positive(authenticated_client: TestClient) -> None:
    assert authenticated_client.get(f"{API}/0").status_code == 422


def test_missing_task_returns_404(authenticated_client: TestClient) -> None:
    assert authenticated_client.get(f"{API}/2147483000").status_code == 404


def test_patch_rejects_null_required_fields_and_clears_nullable_fields(
    authenticated_client: TestClient,
) -> None:
    due_date = (date.today() + timedelta(days=1)).isoformat()
    response = authenticated_client.post(
        API,
        json={
            "title": "Nullable field test",
            "description": "Remove this description",
            "due_date": due_date,
        },
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    assert (
        authenticated_client.patch(f"{API}/{task_id}", json={"title": None}).status_code
        == 422
    )
    cleared = authenticated_client.patch(
        f"{API}/{task_id}", json={"description": None, "due_date": None}
    )
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["due_date"] is None


def test_due_date_cannot_be_in_the_past(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        API,
        json={
            "title": "Past due",
            "due_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 422


def test_created_at_is_utc(authenticated_client: TestClient) -> None:
    task = create_task(authenticated_client)
    created_at = task["created_at"].replace("Z", "+00:00")
    assert datetime.fromisoformat(created_at).utcoffset() == timedelta(0)


def test_task_routes_require_authentication(client: TestClient) -> None:
    assert client.get(API).status_code == 401
