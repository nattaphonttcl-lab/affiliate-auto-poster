import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.cache import InMemoryTTLCache
from app.core.config import get_settings
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.image_engine import (
    DynamicVariables,
    ImageGenerateRequest,
    ImageTemplateCreateRequest,
    ImageTemplateStatus,
    ImageType,
    OutputFormat,
)
from app.schemas.product import ProductPayload
from app.services.image_engine_service import ImageEngineService
from app.services.image_providers import ImageProviderFactory, ImageProviderRegistry
from app.services.image_storage import LocalStorageBackend


def _seed_product(db_session: Session) -> int:
    repo = ProductRepository(db_session)
    item = repo.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/9200",
        normalized_url="https://shopee.co.id/product/1/9200",
        marketplace="shopee",
        external_product_id="9200",
        fingerprint="fp-9200",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/9200",
            external_product_id="9200",
            title="Service Image Product",
            price=Decimal("87.00"),
            original_price=Decimal("100.00"),
            discount="13%",
            rating=4.6,
            sold_count=60,
            images=["https://cdn.example.com/p.jpg"],
            shop_name="Service Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/9200",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="import",
    )
    return item.id


def _build_service(db_session: Session, tmp_path: str) -> ImageEngineService:
    settings = get_settings()
    settings.image_template_cache_ttl_seconds = 300
    settings.image_min_resolution_width = 256
    settings.image_min_resolution_height = 256
    settings.image_provider_failover_order = "local_template"

    return ImageEngineService(
        ProductRepository(db_session),
        AIContentRepository(db_session),
        ImageEngineRepository(db_session),
        ImageProviderRegistry(factory=ImageProviderFactory()),
        LocalStorageBackend(root_dir=tmp_path),
        settings,
        InMemoryTTLCache(),
    )


def _create_template(service: ImageEngineService) -> int:
    template = service.create_template(
        payload=ImageTemplateCreateRequest(
            name="Service Template",
            image_type=ImageType.FACEBOOK_POST,
            canvas_width=1080,
            canvas_height=1080,
            safe_area={"x": 20, "y": 20, "width": 1040, "height": 1040},
            background={"type": "solid", "color": "#ffffff"},
            layers=[{"name": "headline"}],
            fonts={"headline": "DejaVuSans-Bold.ttf"},
            colors={"headline": "#111111"},
            logo_position={"x": 900, "y": 20, "width": 120, "height": 120},
            watermark={"enabled": True, "text": "Affiliate"},
            overlay={"enabled": False},
            dynamic_variables=["product_name", "price", "caption"],
            version=1,
            status=ImageTemplateStatus.ACTIVE,
        ),
        created_by=1,
    )
    return template.id


def test_generate_regenerate_and_history(db_session: Session, tmp_path) -> None:
    product_id = _seed_product(db_session)
    service = _build_service(db_session, str(tmp_path))
    template_id = _create_template(service)

    generated = asyncio.run(
        service.generate(
            payload=ImageGenerateRequest(
                product_id=product_id,
                image_type=ImageType.FACEBOOK_POST,
                provider="local_template",
                model="local-v1",
                output_format=OutputFormat.PNG,
                template_id=template_id,
                variables=DynamicVariables(caption="Buy now"),
            ),
            owner_user_id=1,
        )
    )
    assert generated.generated_image_id > 0
    assert generated.version == 1

    regenerated = asyncio.run(
        service.regenerate(
            generated_image_id=generated.generated_image_id,
            provider=None,
            model=None,
            owner_user_id=1,
        )
    )
    assert regenerated.version == 2

    history = service.history(owner_user_id=1, limit=20, offset=0)
    assert history.total == 2
    assert len(history.items) == 2
