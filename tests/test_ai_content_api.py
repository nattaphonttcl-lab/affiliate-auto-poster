from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import get_ai_content_service
from app.core.cache import InMemoryTTLCache
from app.core.config import get_settings
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductPayload
from app.services.ai_content_service import AIContentService


class _MockProvider:
    _call = 0

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        content_types: list[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ):
        _ = (system_prompt, user_prompt, model, temperature, max_tokens)
        self.__class__._call += 1
        n = self.__class__._call
        return type(
            "Result",
            (),
            {
                "content_by_type": {
                    key: f"Generated {key} for api test #{n} #affiliate"
                    for key in content_types
                },
                "model": model,
                "cost_usd": Decimal("0.0009"),
                "latency_ms": 90,
            },
        )()


class _MockProviderFactory:
    def get_provider(
        self, *, provider_name: str, api_key: str, model: str, base_url: str | None
    ):
        _ = (provider_name, api_key, model, base_url)
        return _MockProvider()


def _create_user_and_token(client: TestClient) -> str:
    client.post(
        "/api/v1/users",
        json={"email": "ai-api@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "ai-api@example.com", "password": "StrongPass123"},
    )
    return login.json()["access_token"]


def _seed_product(db_session: Session) -> int:
    repository = ProductRepository(db_session)
    product = repository.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/9100",
        normalized_url="https://shopee.co.id/product/1/9100",
        marketplace="shopee",
        external_product_id="9100",
        fingerprint="fp-9100",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/9100",
            external_product_id="9100",
            title="API AI Product",
            price=Decimal("120.00"),
            original_price=Decimal("150.00"),
            discount="20%",
            rating=4.9,
            sold_count=100,
            images=["https://cdn.example.com/api-ai.jpg"],
            shop_name="AI API Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/9100",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="import",
    )
    return product.id


def test_ai_api_template_and_generation_flow(
    client: TestClient, db_session: Session
) -> None:
    settings = get_settings()
    settings.ai_provider_encryption_key = "test-encryption-key"

    ai_repo = AIContentRepository(db_session)
    ai_repo.upsert_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        api_key="fake",
        encryption_key=settings.ai_provider_encryption_key,
        base_url=None,
        is_active=True,
    )

    service = AIContentService(
        ProductRepository(db_session),
        ai_repo,
        _MockProviderFactory(),
        settings,
        InMemoryTTLCache(),
    )

    client.app.dependency_overrides[get_ai_content_service] = lambda: service
    try:
        product_id = _seed_product(db_session)
        token = _create_user_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_template = client.post(
            "/api/v1/ai/templates",
            headers=headers,
            json={
                "name": "API Template",
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
        assert create_template.status_code == 201

        generate = client.post(
            "/api/v1/ai/generate",
            headers=headers,
            json={
                "product_id": product_id,
                "platform": "facebook",
                "content_types": ["facebook_caption", "hashtags"],
                "style": "professional",
                "target_audience": "electronics",
                "language": "id",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "benefits": ["portable"],
                "features": ["usb-c"],
            },
        )
        assert generate.status_code == 200
        content_id = generate.json()["content_id"]

        regenerate = client.post(
            "/api/v1/ai/regenerate",
            headers=headers,
            json={"content_id": content_id},
        )
        assert regenerate.status_code == 200
        assert regenerate.json()["version"] == 2

        history = client.get("/api/v1/ai/history", headers=headers)
        assert history.status_code == 200
        assert history.json()["total"] == 1

        templates = client.get("/api/v1/ai/templates", headers=headers)
        assert templates.status_code == 200
        template_id = templates.json()[0]["id"]

        patch = client.patch(
            f"/api/v1/ai/templates/{template_id}",
            headers=headers,
            json={"status": "inactive"},
        )
        assert patch.status_code == 200

        delete = client.delete(f"/api/v1/ai/templates/{template_id}", headers=headers)
        assert delete.status_code == 204
    finally:
        client.app.dependency_overrides.pop(get_ai_content_service, None)
