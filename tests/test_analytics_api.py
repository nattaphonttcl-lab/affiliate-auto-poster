from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analytics_event import AnalyticsEvent


def _create_user_and_token(client: TestClient) -> str:
    client.post("/api/v1/users", json={"email": "analytics@example.com", "password": "StrongPass123"})
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "analytics@example.com", "password": "StrongPass123"},
    )
    return login_response.json()["access_token"]


def _seed_events(db_session: Session) -> None:
    events = [
        AnalyticsEvent(event_type="product_parsed", entity_type="product", entity_id=1, event_metadata={"source": "shopee"}),
        AnalyticsEvent(event_type="caption_generated", entity_type="caption_batch", entity_id=1, event_metadata={"style": "promotion"}),
        AnalyticsEvent(event_type="image_generated", entity_type="promotional_image", entity_id=1, event_metadata={"template": "classic"}),
        AnalyticsEvent(event_type="scheduled_post_created", entity_type="scheduled_post", entity_id=1, event_metadata={"target": "fb-page"}),
    ]
    for event in events:
        db_session.add(event)
    db_session.commit()


def test_analytics_overview_and_events(client: TestClient, db_session: Session) -> None:
    _seed_events(db_session)
    token = _create_user_and_token(client)

    overview_response = client.get(
        "/api/v1/analytics/overview?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["totals"]["product_parsed"] == 1
    assert overview["totals"]["caption_generated"] == 1
    assert overview["totals"]["image_generated"] == 1
    assert overview["totals"]["scheduled_post_created"] == 1
    assert len(overview["daily"]) >= 1

    events_response = client.get(
        "/api/v1/analytics/events?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert events_response.status_code == 200
    items = events_response.json()["items"]
    assert len(items) == 4
    event_types = {item["event_type"] for item in items}
    assert "product_parsed" in event_types
    assert "caption_generated" in event_types
