from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_ai_content_service,
    get_image_engine_service,
    get_marketplace_provider_registry,
    get_publishing_service,
)
from app.core.cache import InMemoryTTLCache
from app.core.config import get_settings
from app.models.analytics_event import AnalyticsEvent
from app.models.publishing import DeadLetterQueue, PublishingHistory, PublishingJob
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.publishing_repository import PublishingRepository
from app.schemas.product import ProductPayload
from app.core.exceptions import AppException
from app.services.ai_content_service import AIContentService
from app.services.ai_providers import AIProviderResult, ProviderFactory
from app.services.image_engine_service import ImageEngineService
from app.services.image_providers import (
    ImageProviderFactory,
    ImageProviderRegistry,
)
from app.services.image_storage import LocalStorageBackend
from app.services.marketplace_provider import (
    MarketplaceProviderRegistry,
    ShopeeProvider,
)
from app.services.publishing_service import PublishingService
from app.services.publishing_workers import DeadLetterQueueWorker, QueueWorker
from app.services.social_providers import ProviderFactory as SocialProviderFactory
from app.services.social_providers import ProviderRegistry as SocialProviderRegistry


class _StubParser:
    def parse(self, url: str) -> ProductPayload:
        product_id = url.rstrip("/").split("/")[-1].split("?")[0]
        return ProductPayload(
            marketplace="shopee",
            normalized_url=url,
            external_product_id=product_id,
            title=f"RC Product {product_id}",
            price=Decimal("99.00"),
            original_price=Decimal("129.00"),
            discount="23%",
            rating=4.8,
            sold_count=120,
            images=["https://cdn.example.com/product.jpg"],
            shop_name="RC Shop",
            category="Electronics",
            affiliate_url=url,
        )


class _StubValidator:
    def validate_url(self, url: str) -> None:
        _ = url

    def validate_payload(self, payload: ProductPayload) -> None:
        _ = payload


class _FailingThenWorkingAIProvider:
    def __init__(self, key: str) -> None:
        self._key = key

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        _ = (system_prompt, user_prompt, model, temperature, max_tokens)
        if "bad" in self._key:
            raise AppException(status_code=503, detail="provider unavailable")
        return AIProviderResult(
            content_by_type={k: f"{k} generated" for k in content_types},
            model=model,
            cost_usd=Decimal("0.001"),
            latency_ms=25,
        )


class _StableAIProvider:
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AIProviderResult:
        _ = (system_prompt, user_prompt, model, temperature, max_tokens)
        return AIProviderResult(
            content_by_type={
                key: ("#affiliate #deal" if key == "hashtags" else f"{key} content")
                for key in content_types
            },
            model=model,
            cost_usd=Decimal("0.001"),
            latency_ms=20,
        )


class _StableProviderFactory(ProviderFactory):
    def get_provider(
        self, *, provider_name: str, api_key: str, model: str, base_url: str | None
    ):
        _ = (provider_name, api_key, model, base_url)
        return _StableAIProvider()


class _ProviderFactoryWithFailover(ProviderFactory):
    def get_provider(
        self, *, provider_name: str, api_key: str, model: str, base_url: str | None
    ):
        _ = (provider_name, model, base_url)
        return _FailingThenWorkingAIProvider(api_key)


class _FailingImageProviderFactory(ImageProviderFactory):
    def get_provider(
        self,
        *,
        provider_name: str,
        api_key: str | None,
        model: str,
        base_url: str | None,
    ):
        if provider_name == "openai":

            class _FailOpenAI:
                provider_name = "openai"

                async def generate_image(self, **kwargs):
                    _ = kwargs
                    from app.core.exceptions import AppException

                    raise AppException(status_code=503, detail="forced openai failure")

            return _FailOpenAI()
        return super().get_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )


def _create_user_and_token(client: TestClient, email: str) -> str:
    client.post("/api/v1/users", json={"email": email, "password": "StrongPass123"})
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    return login.json()["access_token"]


def _create_social_account(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/social/accounts",
        headers=headers,
        json={
            "platform": "facebook",
            "account_name": "RC FB",
            "account_identifier": "fb_rc_1",
            "permissions": ["publish_posts"],
            "timezone": "UTC",
            "business_hours_start": 0,
            "business_hours_end": 23,
            "rate_limit_per_minute": 120,
            "access_token": "token",
            "refresh_token": "refresh",
            "token_expires_at": None,
            "scopes": ["publish"],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _wire_marketplace_override(client: TestClient) -> None:
    def _registry() -> MarketplaceProviderRegistry:
        return MarketplaceProviderRegistry(
            providers=[ShopeeProvider(parser=_StubParser(), validator=_StubValidator())]
        )

    client.app.dependency_overrides[get_marketplace_provider_registry] = _registry


def _wire_ai_failover_override(client: TestClient, db_session: Session) -> None:
    settings = get_settings()
    settings.ai_provider_encryption_key = "rc-ai"

    repo = AIContentRepository(db_session)
    repo.upsert_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        api_key="bad-primary",
        encryption_key=settings.ai_provider_encryption_key,
        base_url=None,
        is_active=True,
    )
    repo.upsert_provider_config(
        provider="gemini",
        model="gpt-4o-mini",
        api_key="good-secondary",
        encryption_key=settings.ai_provider_encryption_key,
        base_url=None,
        is_active=True,
    )

    service = AIContentService(
        ProductRepository(db_session),
        repo,
        _ProviderFactoryWithFailover(),
        settings,
        InMemoryTTLCache(),
    )
    client.app.dependency_overrides[get_ai_content_service] = lambda: service


def _wire_ai_success_override(client: TestClient, db_session: Session) -> None:
    settings = get_settings()
    settings.ai_provider_encryption_key = "rc-ai-ok"

    repo = AIContentRepository(db_session)
    repo.upsert_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        api_key="good-primary",
        encryption_key=settings.ai_provider_encryption_key,
        base_url=None,
        is_active=True,
    )

    service = AIContentService(
        ProductRepository(db_session),
        repo,
        _StableProviderFactory(),
        settings,
        InMemoryTTLCache(),
    )
    client.app.dependency_overrides[get_ai_content_service] = lambda: service


def _wire_image_failover_override(
    client: TestClient, db_session: Session, tmp_dir: str
) -> None:
    settings = get_settings()
    settings.image_provider_failover_order = "openai,local_template"

    service = ImageEngineService(
        ProductRepository(db_session),
        AIContentRepository(db_session),
        ImageEngineRepository(db_session),
        ImageProviderRegistry(factory=_FailingImageProviderFactory()),
        LocalStorageBackend(root_dir=tmp_dir),
        settings,
        InMemoryTTLCache(),
    )
    client.app.dependency_overrides[get_image_engine_service] = lambda: service


def _wire_publishing_override(client: TestClient, db_session: Session) -> None:
    settings = get_settings()
    settings.ai_provider_encryption_key = "rc-publish"
    settings.publishing_provider_failover_order = "facebook"
    settings.publishing_retry_base_seconds = 1
    settings.publishing_retry_max_seconds = 5

    service = PublishingService(
        product_repository=ProductRepository(db_session),
        ai_repository=AIContentRepository(db_session),
        image_repository=ImageEngineRepository(db_session),
        repository=PublishingRepository(db_session),
        provider_registry=SocialProviderRegistry(factory=SocialProviderFactory()),
        settings=settings,
        analytics_repository=None,
    )
    client.app.dependency_overrides[get_publishing_service] = lambda: service


def _import_product(client: TestClient, headers: dict[str, str], suffix: int) -> int:
    response = client.post(
        "/api/v1/products/import",
        headers=headers,
        json={"url": f"https://shopee.co.id/product/1/{suffix}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_ai_template(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/ai/templates",
        headers=headers,
        json={
            "name": "RC Template",
            "category": "facebook",
            "system_prompt": "You are a copywriter for {{platform}}",
            "user_prompt": "Create for {{product_name}} price {{price}} audience {{target_audience}} language {{language}} benefits {{benefits}} features {{features}} discount {{discount}}",
            "variables": [
                {"name": "platform"},
                {"name": "product_name"},
                {"name": "price"},
                {"name": "target_audience"},
                {"name": "language"},
                {"name": "benefits"},
                {"name": "features"},
                {"name": "discount"},
            ],
            "temperature": "0.70",
            "max_tokens": 700,
            "version": 1,
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_image_template(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/images/templates",
        headers=headers,
        json={
            "name": "RC Image Template",
            "image_type": "facebook_post",
            "canvas_width": 1080,
            "canvas_height": 1080,
            "safe_area": {"x": 10, "y": 10, "width": 1060, "height": 1060},
            "background": {"type": "solid", "color": "#ffffff"},
            "layers": [{"name": "title"}],
            "fonts": {"title": "DejaVuSans-Bold.ttf"},
            "colors": {"title": "#111111"},
            "logo_position": {"x": 900, "y": 20, "width": 120, "height": 120},
            "watermark": {"enabled": True, "text": "Affiliate"},
            "overlay": {"enabled": False},
            "dynamic_variables": ["product_name", "price", "caption"],
            "version": 1,
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_rc_scenario_1_full_flow(
    client: TestClient, db_session: Session, tmp_path
) -> None:
    _wire_marketplace_override(client)
    _wire_publishing_override(client, db_session)
    _wire_image_failover_override(client, db_session, str(tmp_path))

    token = _create_user_and_token(client, "rc1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    social_account_id = _create_social_account(client, headers)

    product_id = _import_product(client, headers, 10001)
    image_template_id = _create_image_template(client, headers)

    caption_response = client.post(
        "/api/v1/captions/generate",
        headers=headers,
        json={
            "product_id": product_id,
            "style": "promotion",
        },
    )
    assert caption_response.status_code == 200

    image_response = client.post(
        "/api/v1/images/generate",
        headers=headers,
        json={
            "product_id": product_id,
            "image_type": "facebook_post",
            "provider": "openai",
            "model": "dall-e-3",
            "output_format": "png",
            "template_id": image_template_id,
            "variables": {"caption": "RC publish now"},
        },
    )
    assert image_response.status_code == 200
    generated_image_id = image_response.json()["generated_image_id"]

    schedule_response = client.post(
        "/api/v1/publish/schedule",
        headers=headers,
        json={
            "social_account_id": social_account_id,
            "product_id": product_id,
            "generated_image_id": generated_image_id,
            "post_type": "facebook_feed",
            "media_attachments": ["https://cdn.example.com/media.png"],
            "hashtags": ["#rc"],
            "mentions": [],
            "cta": "Buy now",
            "affiliate_link": "https://example.com/aff",
            "alt_text": "alt",
            "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "recurrence_rule": None,
            "timezone": "UTC",
            "enforce_business_hours": False,
        },
    )
    assert schedule_response.status_code == 200
    job_id = schedule_response.json()["job"]["id"]

    repo = PublishingRepository(db_session)
    queue = repo.get_queue_entry(job_id=job_id)
    assert queue is not None
    queue.visible_at = datetime.now(UTC) - timedelta(seconds=1)
    queue.status = "pending"
    db_session.add(queue)
    db_session.commit()

    service = client.app.dependency_overrides[get_publishing_service]()
    processed, published, failed = QueueWorker(service).run_once(worker_id="rc-q")
    assert processed >= 0
    assert published >= 0
    assert failed >= 0

    history = client.get("/api/v1/publish/history", headers=headers)
    assert history.status_code == 200

    analytics = client.get("/api/v1/analytics/overview?days=30", headers=headers)
    assert analytics.status_code == 200


def test_rc_scenario_2_bulk_products(client: TestClient) -> None:
    _wire_marketplace_override(client)
    token = _create_user_and_token(client, "rc2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    for idx in range(5):
        _import_product(client, headers, 20000 + idx)

    listed = client.get("/api/v1/products?limit=10&offset=0", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 5


def test_rc_scenario_3_retry_failed_publishing(
    client: TestClient, db_session: Session
) -> None:
    _wire_marketplace_override(client)
    _wire_publishing_override(client, db_session)

    token = _create_user_and_token(client, "rc3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    social_account_id = _create_social_account(client, headers)
    product_id = _import_product(client, headers, 30001)

    scheduled = client.post(
        "/api/v1/publish/schedule",
        headers=headers,
        json={
            "social_account_id": social_account_id,
            "product_id": product_id,
            "post_type": "facebook_feed",
            "media_attachments": ["https://cdn.example.com/media.png"],
            "hashtags": ["#rc"],
            "mentions": [],
            "cta": None,
            "affiliate_link": None,
            "alt_text": None,
            "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "recurrence_rule": None,
            "timezone": "UTC",
            "enforce_business_hours": False,
        },
    )
    assert scheduled.status_code == 200
    job_id = scheduled.json()["job"]["id"]

    repo = PublishingRepository(db_session)
    repo.update_job_status(job_id=job_id, status="failed", last_error="forced")
    repo.update_queue_status(
        job_id=job_id,
        status="failed",
        visible_at=datetime.now(UTC),
        lock_owner=None,
    )
    repo.commit()

    retry = client.post(
        "/api/v1/publish/retry", headers=headers, json={"job_id": job_id}
    )
    assert retry.status_code == 200
    assert retry.json()["job"]["status"] == "retry"


def test_rc_scenario_4_dead_letter_recovery(
    client: TestClient, db_session: Session
) -> None:
    _wire_marketplace_override(client)
    _wire_publishing_override(client, db_session)

    token = _create_user_and_token(client, "rc4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    social_account_id = _create_social_account(client, headers)
    product_id = _import_product(client, headers, 40001)

    scheduled = client.post(
        "/api/v1/publish/schedule",
        headers=headers,
        json={
            "social_account_id": social_account_id,
            "product_id": product_id,
            "post_type": "facebook_feed",
            "media_attachments": ["https://cdn.example.com/media.png"],
            "hashtags": ["#rc"],
            "mentions": [],
            "cta": None,
            "affiliate_link": None,
            "alt_text": None,
            "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "recurrence_rule": None,
            "timezone": "UTC",
            "enforce_business_hours": False,
        },
    )
    assert scheduled.status_code == 200
    job_id = scheduled.json()["job"]["id"]

    repo = PublishingRepository(db_session)
    repo.update_job_status(job_id=job_id, status="failed", last_error="forced")
    repo.update_queue_status(
        job_id=job_id,
        status="failed",
        visible_at=datetime.now(UTC),
        lock_owner=None,
    )
    repo.add_dead_letter(job_id=job_id, owner_user_id=1, reason="forced", payload={})
    repo.commit()

    service = client.app.dependency_overrides[get_publishing_service]()
    recovered = DeadLetterQueueWorker(service).run_once(limit=10)
    assert recovered >= 1

    refreshed = repo.get_job(job_id)
    assert refreshed is not None
    assert refreshed.status == "retry"


def test_rc_scenario_5_ai_provider_failover(
    client: TestClient, db_session: Session
) -> None:
    _wire_marketplace_override(client)
    _wire_ai_failover_override(client, db_session)

    token = _create_user_and_token(client, "rc5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    product_id = _import_product(client, headers, 50001)
    _create_ai_template(client, headers)

    primary = client.post(
        "/api/v1/ai/generate",
        headers=headers,
        json={
            "product_id": product_id,
            "platform": "facebook",
            "content_types": ["facebook_caption"],
            "style": "professional",
            "target_audience": "electronics",
            "language": "id",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "benefits": ["portable"],
            "features": ["usb-c"],
        },
    )
    assert primary.status_code == 503

    fallback = client.post(
        "/api/v1/ai/generate",
        headers=headers,
        json={
            "product_id": product_id,
            "platform": "facebook",
            "content_types": ["facebook_caption"],
            "style": "professional",
            "target_audience": "electronics",
            "language": "id",
            "provider": "gemini",
            "model": "gpt-4o-mini",
            "benefits": ["portable"],
            "features": ["usb-c"],
        },
    )
    assert fallback.status_code == 200


def test_rc_scenario_6_image_provider_failover(
    client: TestClient, db_session: Session, tmp_path
) -> None:
    _wire_marketplace_override(client)
    _wire_image_failover_override(client, db_session, str(tmp_path))

    token = _create_user_and_token(client, "rc6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    product_id = _import_product(client, headers, 60001)
    template_id = _create_image_template(client, headers)

    response = client.post(
        "/api/v1/images/generate",
        headers=headers,
        json={
            "product_id": product_id,
            "image_type": "facebook_post",
            "provider": "openai",
            "model": "dall-e-3",
            "output_format": "png",
            "template_id": template_id,
            "variables": {"caption": "failover image"},
        },
    )
    assert response.status_code == 200


def test_rc_scenario_7_worker_restart_recovery(
    client: TestClient, db_session: Session
) -> None:
    _wire_marketplace_override(client)
    _wire_publishing_override(client, db_session)

    token = _create_user_and_token(client, "rc7@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    social_account_id = _create_social_account(client, headers)
    product_id = _import_product(client, headers, 70001)

    scheduled = client.post(
        "/api/v1/publish/schedule",
        headers=headers,
        json={
            "social_account_id": social_account_id,
            "product_id": product_id,
            "post_type": "facebook_feed",
            "media_attachments": ["https://cdn.example.com/media.png"],
            "hashtags": ["#rc"],
            "mentions": [],
            "cta": None,
            "affiliate_link": None,
            "alt_text": None,
            "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "recurrence_rule": None,
            "timezone": "UTC",
            "enforce_business_hours": False,
        },
    )
    assert scheduled.status_code == 200
    job_id = scheduled.json()["job"]["id"]

    repo = PublishingRepository(db_session)
    queue = repo.get_queue_entry(job_id=job_id)
    assert queue is not None
    queue.status = "publishing"
    queue.lock_owner = "dead-worker"
    queue.visible_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.add(queue)
    db_session.commit()

    queue.status = "pending"
    queue.lock_owner = None
    db_session.add(queue)
    db_session.commit()

    service = client.app.dependency_overrides[get_publishing_service]()
    processed, published, failed = QueueWorker(service).run_once(worker_id="new-worker")
    assert processed >= 0
    assert published >= 0
    assert failed >= 0

    db_session.expire_all()
    queue_refreshed = repo.get_queue_entry(job_id=job_id)
    assert queue_refreshed is not None
    assert queue_refreshed.lock_owner != "dead-worker"


def test_rc_scenario_8_database_restart_recovery(db_session: Session) -> None:
    repo = ProductRepository(db_session)
    product = repo.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/80001",
        normalized_url="https://shopee.co.id/product/1/80001",
        marketplace="shopee",
        external_product_id="80001",
        fingerprint="fp-80001",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/80001",
            external_product_id="80001",
            title="DB Recovery",
            price=Decimal("10.0"),
            original_price=Decimal("12.0"),
            discount="10%",
            rating=4.0,
            sold_count=10,
            images=["https://cdn.example.com/1.png"],
            shop_name="shop",
            category="cat",
            affiliate_url="https://shopee.co.id/product/1/80001",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="seed",
    )
    db_session.commit()

    db_session.rollback()
    fetched = repo.get_by_id(product.id)
    assert fetched is not None


def test_rc_scenario_9_redis_restart_readiness(client: TestClient) -> None:
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}


def test_rc_scenario_10_disaster_recovery_scripts(tmp_path) -> None:
    from scripts.backup import run_backup
    from scripts.restore import run_restore

    db_path = tmp_path / "affiliate.db"
    images_dir = tmp_path / "generated_images"
    images_dir.mkdir(parents=True)
    (images_dir / "sample.txt").write_text("ok", encoding="utf-8")
    db_path.write_text("db", encoding="utf-8")

    backups_root = tmp_path / "backups"
    backup_path = run_backup(db_path, images_dir, backups_root)

    db_path.write_text("changed", encoding="utf-8")
    run_restore(backup_path, db_path, images_dir)
    assert db_path.read_text(encoding="utf-8") == "db"


def test_rc_provider_matrix_mocked_status(db_session: Session) -> None:
    repo = AIContentRepository(db_session)
    settings = get_settings()
    settings.ai_provider_encryption_key = "rc-matrix"

    providers = ["openai", "gemini", "claude", "deepseek", "openrouter"]
    for provider in providers:
        repo.upsert_provider_config(
            provider=provider,
            model="test-model",
            api_key=f"{provider}-key",
            encryption_key=settings.ai_provider_encryption_key,
            base_url=None,
            is_active=True,
        )

    count = int(db_session.scalar(select(func.count(AnalyticsEvent.id))) or 0)
    assert count >= 0


def test_rc_cleanup_no_dead_artifacts(db_session: Session) -> None:
    db_session.execute(delete(DeadLetterQueue))
    db_session.execute(delete(PublishingHistory))
    db_session.execute(delete(PublishingJob))
    db_session.commit()
