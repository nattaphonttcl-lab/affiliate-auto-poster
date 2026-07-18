from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.scheduled_post import ScheduledPost


def _create_user_and_token(client: TestClient, email: str) -> tuple[int, str]:
    create_response = client.post(
        "/api/v1/users", json={"email": email, "password": "StrongPass123"}
    )
    user_id = create_response.json()["id"]
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    return user_id, login_response.json()["access_token"]


def _create_product(client: TestClient, token: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/products/shopee",
        json={"url": "https://shopee.co.id/p/scheduler"},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_create_scheduled_post_rejects_past_time(
    client: TestClient, shopee_service_with_static_parser
) -> None:
    _ = shopee_service_with_static_parser
    _, token = _create_user_and_token(client, "scheduler-past@example.com")
    product_id = _create_product(client, token)

    response = client.post(
        "/api/v1/scheduler/posts",
        json={
            "product_id": product_id,
            "target": "fb-page-1",
            "scheduled_for": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "platform": "facebook",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_scheduler_run_publishes_due_post(
    client: TestClient,
    db_session: Session,
    shopee_service_with_static_parser,
) -> None:
    _ = shopee_service_with_static_parser
    _, token = _create_user_and_token(client, "scheduler-run@example.com")
    product_id = _create_product(client, token)

    create_response = client.post(
        "/api/v1/scheduler/posts",
        json={
            "product_id": product_id,
            "target": "fb-page-1",
            "scheduled_for": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
            "platform": "facebook",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    scheduled_post_id = create_response.json()["id"]

    scheduled_post = db_session.get(ScheduledPost, scheduled_post_id)
    assert scheduled_post is not None
    scheduled_post.scheduled_for = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(scheduled_post)
    db_session.commit()

    run_without_confirmation = client.post(
        "/api/v1/scheduler/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_without_confirmation.status_code == 200
    assert run_without_confirmation.json()["processed"] == 0
    assert run_without_confirmation.json()["published"] == 0

    confirm_response = client.post(
        f"/api/v1/scheduler/posts/{scheduled_post_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["state"] == "confirmed"

    confirm_response_again = client.post(
        f"/api/v1/scheduler/posts/{scheduled_post_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_response_again.status_code == 200
    assert confirm_response_again.json()["state"] == "confirmed"

    run_response = client.post(
        "/api/v1/scheduler/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_response.status_code == 200
    assert run_response.json()["processed"] == 1
    assert run_response.json()["published"] == 1
    assert run_response.json()["failed"] == 0

    # Running again should not duplicate processing/publishing.
    run_response_again = client.post(
        "/api/v1/scheduler/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_response_again.status_code == 200
    assert run_response_again.json()["processed"] == 0
    assert run_response_again.json()["published"] == 0

    list_response = client.get(
        "/api/v1/scheduler/posts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["state"] == "published"


def test_scheduler_enforces_owner_authorization(
    client: TestClient,
    db_session: Session,
    shopee_service_with_static_parser,
) -> None:
    _ = shopee_service_with_static_parser
    _, owner_token = _create_user_and_token(client, "scheduler-owner@example.com")
    _, intruder_token = _create_user_and_token(client, "scheduler-intruder@example.com")

    product_id = _create_product(client, owner_token)

    create_response = client.post(
        "/api/v1/scheduler/posts",
        json={
            "product_id": product_id,
            "target": "fb-page-owner",
            "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "platform": "facebook",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert create_response.status_code == 201
    scheduled_post_id = create_response.json()["id"]

    unauthorized_confirm = client.post(
        f"/api/v1/scheduler/posts/{scheduled_post_id}/confirm",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert unauthorized_confirm.status_code == 403

    # Intruder should not see owner's scheduled posts.
    intruder_list = client.get(
        "/api/v1/scheduler/posts",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert intruder_list.status_code == 200
    assert intruder_list.json() == []


def test_confirm_missing_scheduled_post_returns_404(client: TestClient) -> None:
    _, token = _create_user_and_token(client, "scheduler-missing@example.com")
    response = client.post(
        "/api/v1/scheduler/posts/99999/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
