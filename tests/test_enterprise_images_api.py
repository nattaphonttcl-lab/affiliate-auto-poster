from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_image_engine_service
from app.core.cache import InMemoryTTLCache
from app.core.config import get_settings
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductPayload
from app.services.image_engine_service import ImageEngineService
from app.services.image_providers import ImageProviderFactory, ImageProviderRegistry
from app.services.image_storage import LocalStorageBackend


def _create_user_and_token(client: TestClient) -> str:
    client.post(
        "/api/v1/users",
        json={"email": "enterprise-images@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "enterprise-images@example.com", "password": "StrongPass123"},
    )
    return login.json()["access_token"]


def _seed_product(db_session: Session) -> int:
    repo = ProductRepository(db_session)
    product = repo.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/9300",
        normalized_url="https://shopee.co.id/product/1/9300",
        marketplace="shopee",
        external_product_id="9300",
        fingerprint="fp-9300",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/9300",
            external_product_id="9300",
            title="API Enterprise Image Product",
            price=Decimal("199.00"),
            original_price=Decimal("250.00"),
            discount="20%",
            rating=4.9,
            sold_count=500,
            images=["https://cdn.example.com/product-enterprise.jpg"],
            shop_name="Enterprise Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/9300",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="import",
    )
    return product.id


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


def test_enterprise_images_api_flow(
    client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    service = _build_service(db_session, str(tmp_path))
    client.app.dependency_overrides[get_image_engine_service] = lambda: service

    try:
        token = _create_user_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        product_id = _seed_product(db_session)

        create_template = client.post(
            "/api/v1/images/templates",
            headers=headers,
            json={
                "name": "Enterprise API Template",
                "image_type": "facebook_post",
                "canvas_width": 1080,
                "canvas_height": 1080,
                "safe_area": {"x": 20, "y": 20, "width": 1040, "height": 1040},
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
        assert create_template.status_code == 201
        template_id = create_template.json()["id"]

        generate = client.post(
            "/api/v1/images/generate",
            headers=headers,
            json={
                "product_id": product_id,
                "image_type": "facebook_post",
                "provider": "local_template",
                "model": "local-v1",
                "output_format": "png",
                "template_id": template_id,
                "variables": {"caption": "Flash sale now"},
            },
        )
        assert generate.status_code == 200
        generated_image_id = generate.json()["generated_image_id"]

        regenerate = client.post(
            "/api/v1/images/regenerate",
            headers=headers,
            json={"generated_image_id": generated_image_id},
        )
        assert regenerate.status_code == 200

        history = client.get("/api/v1/images/history", headers=headers)
        assert history.status_code == 200
        assert history.json()["total"] >= 2

        preview = client.post(
            "/api/v1/images/preview",
            headers=headers,
            json={
                "product_id": product_id,
                "image_type": "facebook_post",
                "template_id": template_id,
                "variables": {"caption": "Preview copy"},
            },
        )
        assert preview.status_code == 200

        patch = client.patch(
            f"/api/v1/images/templates/{template_id}",
            headers=headers,
            json={"status": "inactive"},
        )
        assert patch.status_code == 200

        delete = client.delete(
            f"/api/v1/images/templates/{template_id}", headers=headers
        )
        assert delete.status_code == 204
    finally:
        client.app.dependency_overrides.pop(get_image_engine_service, None)
