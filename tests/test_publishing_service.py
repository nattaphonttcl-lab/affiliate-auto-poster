from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publishing_repository import PublishingRepository
from app.schemas.product import ProductPayload
from app.schemas.publishing import (
    PublishCancelRequest,
    PublishRequest,
    PublishRetryRequest,
    PublishScheduleRequest,
    SocialAccountCreateRequest,
    SocialPostType,
    SocialPlatform,
)
from app.services.publishing_service import PublishingService
from app.services.social_providers import ProviderFactory, ProviderRegistry


def _seed_product(db_session: Session) -> int:
    repo = ProductRepository(db_session)
    product = repo.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/6201",
        normalized_url="https://shopee.co.id/product/1/6201",
        marketplace="shopee",
        external_product_id="6201",
        fingerprint="publish-fp-6201",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/6201",
            external_product_id="6201",
            title="Publish Product",
            price=Decimal("99.00"),
            original_price=Decimal("129.00"),
            discount="23%",
            rating=4.8,
            sold_count=100,
            images=["https://cdn.example.com/publish.jpg"],
            shop_name="Publish Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/6201",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="seed",
    )
    return product.id


def _build_service(db_session: Session) -> PublishingService:
    settings = get_settings()
    settings.ai_provider_encryption_key = "publish-test-key"
    settings.publishing_provider_failover_order = (
        "facebook,facebook_page,instagram,threads,tiktok,youtube_shorts,shopee_video"
    )
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


def test_publish_schedule_retry_cancel_flow(db_session: Session) -> None:
    service = _build_service(db_session)
    product_id = _seed_product(db_session)

    account = service.create_social_account(
        owner_user_id=1,
        payload=SocialAccountCreateRequest(
            platform=SocialPlatform.FACEBOOK,
            account_name="Main FB",
            account_identifier="fb_page_1",
            permissions=["publish_posts"],
            timezone="UTC",
            business_hours_start=8,
            business_hours_end=22,
            rate_limit_per_minute=120,
            access_token="token",
            refresh_token="refresh",
            token_expires_at=None,
            scopes=["publish"],
        ),
    )

    immediate = service.publish_now(
        owner_user_id=1,
        payload=PublishRequest(
            social_account_id=account.id,
            product_id=product_id,
            post_type=SocialPostType.FACEBOOK_FEED,
            media_attachments=["https://cdn.example.com/1.jpg"],
            hashtags=["#sale"],
            mentions=["@shop"],
            cta="Buy",
            affiliate_link="https://example.com/a",
            alt_text="alt",
        ),
    )
    assert immediate.job.status == "published"

    scheduled = service.schedule_publish(
        owner_user_id=1,
        payload=PublishScheduleRequest(
            social_account_id=account.id,
            product_id=product_id,
            post_type=SocialPostType.FACEBOOK_FEED,
            media_attachments=["https://cdn.example.com/2.jpg"],
            hashtags=["#sale"],
            mentions=[],
            cta=None,
            affiliate_link=None,
            alt_text=None,
            scheduled_for=datetime.now(UTC) + timedelta(minutes=10),
            recurrence_rule="FREQ=DAILY",
            timezone="UTC",
            enforce_business_hours=True,
        ),
    )
    assert scheduled.job.status == "scheduled"

    cancelled = service.cancel_publish(
        owner_user_id=1,
        payload=PublishCancelRequest(job_id=scheduled.job.id),
    )
    assert cancelled.job.status == "cancelled"

    repo = PublishingRepository(db_session)
    repo.update_job_status(
        job_id=scheduled.job.id,
        status="failed",
        last_error="forced failure",
    )
    repo.update_queue_status(
        job_id=scheduled.job.id,
        status="failed",
        visible_at=datetime.now(UTC),
        lock_owner=None,
    )
    repo.commit()

    retry_req = service.retry_publish(
        owner_user_id=1,
        payload=PublishRetryRequest(job_id=cancelled.job.id),
    )
    assert retry_req.job.status == "retry"
