from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.caption import CaptionBatch
from app.models.product import Product
from app.models.promotional_image import PromotionalImage
from app.models.scheduled_post import ScheduledPost


def _create_user_and_token(client: TestClient) -> tuple[int, str]:
    create_response = client.post(
        "/api/v1/users",
        json={"email": "dashboard@example.com", "password": "StrongPass123"},
    )
    user_id = create_response.json()["id"]
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "dashboard@example.com", "password": "StrongPass123"},
    )
    return user_id, login_response.json()["access_token"]


def _seed_dashboard_data(db_session: Session, owner_user_id: int) -> None:
    now = datetime.now(UTC)
    product = Product(
        source_url="https://shopee.co.id/p/dashboard",
        normalized_url="https://shopee.co.id/p/dashboard",
        marketplace="shopee",
        external_product_id="dashboard",
        fingerprint="dashboard-fingerprint",
        aggregate_version=1,
        title="Dashboard Product",
        price=Decimal("99.00"),
        original_price=Decimal("129.00"),
        discount="23%",
        rating=4.8,
        sold_count=330,
        images=["https://cdn.example.com/product.png"],
        shop_name="Dashboard Shop",
        category="Tools",
        affiliate_url="https://aff.example.com/dashboard",
        expires_at=now + timedelta(days=1),
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    caption_batch = CaptionBatch(
        product_id=product.id, style="promotion", prompt_template="template"
    )
    db_session.add(caption_batch)
    db_session.commit()
    db_session.refresh(caption_batch)

    image = PromotionalImage(
        product_id=product.id,
        template_name="classic",
        output_format="png",
        width=820,
        height=312,
        image_path="generated_images/sample.png",
        product_image_url="https://cdn.example.com/product.png",
        shop_logo_url=None,
    )
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)

    scheduled_post = ScheduledPost(
        owner_user_id=owner_user_id,
        product_id=product.id,
        caption_batch_id=caption_batch.id,
        promotional_image_id=image.id,
        platform="facebook",
        target="fb-page-1",
        scheduled_for=now + timedelta(hours=1),
        state="awaiting_confirmation",
        version=1,
    )
    db_session.add(scheduled_post)
    db_session.commit()


def test_dashboard_summary_and_activities(
    client: TestClient, db_session: Session
) -> None:
    owner_user_id, token = _create_user_and_token(client)
    _seed_dashboard_data(db_session, owner_user_id=owner_user_id)

    summary_response = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["totals"]["products"] == 1
    assert summary["totals"]["caption_batches"] == 1
    assert summary["totals"]["promotional_images"] == 1
    assert summary["totals"]["scheduled_posts"] == 1
    assert summary["scheduler"]["awaiting_confirmation"] == 1

    activity_response = client.get(
        "/api/v1/dashboard/activities?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activity_response.status_code == 200
    items = activity_response.json()["items"]
    assert len(items) >= 3
    item_types = {item["type"] for item in items}
    assert "caption_batch" in item_types
    assert "promotional_image" in item_types
    assert "scheduled_post" in item_types
