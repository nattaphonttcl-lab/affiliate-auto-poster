from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.scheduled_post import ScheduledPost


def _create_user_and_token(client: TestClient) -> str:
    client.post("/api/v1/users", json={"email": "scheduler@example.com", "password": "StrongPass123"})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "scheduler@example.com", "password": "StrongPass123"},
    )
    return login_response.json()["access_token"]


def _create_product(client: TestClient, token: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/products/shopee", json={"url": "https://shopee.co.id/p/scheduler"}, headers=headers)
    assert response.status_code == 200
    return response.json()["id"]


def test_create_scheduled_post_rejects_past_time(client: TestClient, shopee_service_with_static_parser) -> None:
    _ = shopee_service_with_static_parser
    token = _create_user_and_token(client)
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
    token = _create_user_and_token(client)
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

    run_response = client.post(
        "/api/v1/scheduler/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_response.status_code == 200
    assert run_response.json()["processed"] == 1
    assert run_response.json()["published"] == 1
    assert run_response.json()["failed"] == 0

    list_response = client.get(
        "/api/v1/scheduler/posts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "published"
