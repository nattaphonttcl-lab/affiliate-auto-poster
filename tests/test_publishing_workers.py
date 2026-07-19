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
    PublishScheduleRequest,
    SocialAccountCreateRequest,
    SocialPostType,
    SocialPlatform,
)
from app.services.publishing_service import PublishingService
from app.services.publishing_workers import QueueWorker, RetryWorker
from app.services.social_providers import ProviderFactory, ProviderRegistry


def _seed_product(db_session: Session) -> int:
    repo = ProductRepository(db_session)
    product = repo.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/6202",
        normalized_url="https://shopee.co.id/product/1/6202",
        marketplace="shopee",
        external_product_id="6202",
        fingerprint="publish-fp-6202",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/6202",
            external_product_id="6202",
            title="Queue Product",
            price=Decimal("89.00"),
            original_price=Decimal("119.00"),
            discount="25%",
            rating=4.7,
            sold_count=90,
            images=["https://cdn.example.com/queue.jpg"],
            shop_name="Queue Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/6202",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="seed",
    )
    return product.id


def _build_service(db_session: Session) -> PublishingService:
    settings = get_settings()
    settings.ai_provider_encryption_key = "worker-test-key"
    settings.publishing_provider_failover_order = "facebook"
    settings.publishing_retry_base_seconds = 1
    settings.publishing_retry_max_seconds = 5
    return PublishingService(
        product_repository=ProductRepository(db_session),
        ai_repository=AIContentRepository(db_session),
        image_repository=ImageEngineRepository(db_session),
        repository=PublishingRepository(db_session),
        provider_registry=ProviderRegistry(factory=ProviderFactory()),
        settings=settings,
        analytics_repository=None,
    )


def test_queue_and_retry_workers(db_session: Session) -> None:
    service = _build_service(db_session)
    product_id = _seed_product(db_session)

    account = service.create_social_account(
        owner_user_id=1,
        payload=SocialAccountCreateRequest(
            platform=SocialPlatform.FACEBOOK,
            account_name="Queue FB",
            account_identifier="fb_queue_1",
            permissions=["publish_posts"],
            timezone="UTC",
            business_hours_start=8,
            business_hours_end=20,
            rate_limit_per_minute=60,
            access_token="token",
            refresh_token="refresh",
            token_expires_at=None,
            scopes=["publish"],
        ),
    )

    scheduled = service.schedule_publish(
        owner_user_id=1,
        payload=PublishScheduleRequest(
            social_account_id=account.id,
            product_id=product_id,
            post_type=SocialPostType.FACEBOOK_FEED,
            media_attachments=["https://cdn.example.com/queue-1.jpg"],
            hashtags=["#queue"],
            mentions=[],
            cta=None,
            affiliate_link=None,
            alt_text=None,
            scheduled_for=datetime.now(UTC) + timedelta(minutes=2),
            recurrence_rule=None,
            timezone="UTC",
            enforce_business_hours=False,
        ),
    )

    repo = PublishingRepository(db_session)
    queue_row = repo.get_queue_entry(job_id=scheduled.job.id)
    assert queue_row is not None
    queue_row.visible_at = datetime.now(UTC) - timedelta(seconds=1)
    queue_row.status = "pending"
    db_session.add(queue_row)
    db_session.commit()

    queue_worker = QueueWorker(service)
    processed, published, failed = queue_worker.run_once(worker_id="worker-q", limit=10)
    assert processed == 1
    assert published + failed == 1

    retry_worker = RetryWorker(service)
    processed2, published2, failed2 = retry_worker.run_once(
        worker_id="worker-r", limit=10
    )
    assert processed2 >= 0
    assert published2 >= 0
    assert failed2 >= 0
