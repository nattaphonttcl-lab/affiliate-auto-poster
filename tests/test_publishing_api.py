from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_publishing_service
from app.core.config import get_settings
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publishing_repository import PublishingRepository
from app.schemas.product import ProductPayload
from app.services.publishing_service import PublishingService
from app.services.social_providers import ProviderFactory, ProviderRegistry


def _create_user_and_token(client: TestClient, email: str) -> str:
    client.post("/api/v1/users", json={"email": email, "password": "StrongPass123"})
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "StrongPass123"}
    )
    return login.json()["access_token"]


def _seed_product(db_session: Session) -> int:
    repo = ProductRepository(db_session)
    product = repo.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/6203",
        normalized_url="https://shopee.co.id/product/1/6203",
        marketplace="shopee",
        external_product_id="6203",
        fingerprint="publish-fp-6203",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/6203",
            external_product_id="6203",
            title="API Publish Product",
            price=Decimal("79.00"),
            original_price=Decimal("109.00"),
            discount="27%",
            rating=4.9,
            sold_count=99,
            images=["https://cdn.example.com/api-pub.jpg"],
            shop_name="API Publish Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/6203",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="seed",
    )
    return product.id


def _build_service(db_session: Session) -> PublishingService:
    settings = get_settings()
    settings.ai_provider_encryption_key = "api-publish-test-key"
    settings.publishing_provider_failover_order = "facebook"
    settings.publishing_retry_base_seconds = 1
    settings.publishing_retry_max_seconds = 30
    return PublishingService(
        product_repository=ProductRepository(db_session),
        ai_repository=AIContentRepository(db_session),
        image_repository=ImageEngineRepository(db_session),
        repository=PublishingRepository(db_session),
        provider_registry=ProviderRegistry(factory=ProviderFactory()),
        settings=settings,
        analytics_repository=None,
    )


def test_publishing_api_endpoints(client: TestClient, db_session: Session) -> None:
    service = _build_service(db_session)
    client.app.dependency_overrides[get_publishing_service] = lambda: service

    try:
        token = _create_user_and_token(client, "publishing-api@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        product_id = _seed_product(db_session)

        create_account = client.post(
            "/api/v1/social/accounts",
            headers=headers,
            json={
                "platform": "facebook",
                "account_name": "API FB",
                "account_identifier": "fb_api_1",
                "permissions": ["publish_posts"],
                "timezone": "UTC",
                "business_hours_start": 8,
                "business_hours_end": 20,
                "rate_limit_per_minute": 120,
                "access_token": "token",
                "refresh_token": "refresh",
                "token_expires_at": None,
                "scopes": ["publish"],
            },
        )
        assert create_account.status_code == 201
        social_account_id = create_account.json()["id"]

        publish_now = client.post(
            "/api/v1/publish",
            headers=headers,
            json={
                "social_account_id": social_account_id,
                "product_id": product_id,
                "post_type": "facebook_feed",
                "media_attachments": ["https://cdn.example.com/pub-now.jpg"],
                "hashtags": ["#now"],
                "mentions": ["@shop"],
                "cta": "Buy now",
                "affiliate_link": "https://example.com/aff",
                "alt_text": "alt",
            },
        )
        assert publish_now.status_code == 200
        assert publish_now.json()["job"]["status"] == "published"

        schedule = client.post(
            "/api/v1/publish/schedule",
            headers=headers,
            json={
                "social_account_id": social_account_id,
                "product_id": product_id,
                "post_type": "facebook_feed",
                "media_attachments": ["https://cdn.example.com/pub-schedule.jpg"],
                "hashtags": ["#later"],
                "mentions": [],
                "cta": None,
                "affiliate_link": None,
                "alt_text": None,
                "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                "recurrence_rule": "FREQ=DAILY",
                "timezone": "UTC",
                "enforce_business_hours": True,
            },
        )
        assert schedule.status_code == 200
        job_id = schedule.json()["job"]["id"]

        cancel = client.post(
            "/api/v1/publish/cancel",
            headers=headers,
            json={"job_id": job_id},
        )
        assert cancel.status_code == 200
        assert cancel.json()["job"]["status"] == "cancelled"

        repo = PublishingRepository(db_session)
        repo.update_job_status(
            job_id=job_id,
            status="failed",
            last_error="forced failure",
        )
        repo.update_queue_status(
            job_id=job_id,
            status="failed",
            visible_at=datetime.now(UTC),
            lock_owner=None,
        )
        repo.commit()

        retry = client.post(
            "/api/v1/publish/retry",
            headers=headers,
            json={"job_id": job_id},
        )
        assert retry.status_code == 200
        assert retry.json()["job"]["status"] == "retry"

        jobs = client.get("/api/v1/publish/jobs", headers=headers)
        assert jobs.status_code == 200
        assert jobs.json()["total"] >= 2

        history = client.get("/api/v1/publish/history", headers=headers)
        assert history.status_code == 200
        assert history.json()["total"] >= 1

        accounts = client.get("/api/v1/social/accounts", headers=headers)
        assert accounts.status_code == 200
        assert len(accounts.json()) == 1

        patch_account = client.patch(
            f"/api/v1/social/accounts/{social_account_id}",
            headers=headers,
            json={"account_name": "API FB Updated", "is_active": True},
        )
        assert patch_account.status_code == 200

        delete_account = client.delete(
            f"/api/v1/social/accounts/{social_account_id}",
            headers=headers,
        )
        assert delete_account.status_code == 204
    finally:
        client.app.dependency_overrides.pop(get_publishing_service, None)
