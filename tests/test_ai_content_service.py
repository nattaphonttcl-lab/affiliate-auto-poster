import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.cache import InMemoryTTLCache
from app.core.config import get_settings
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.ai_content import (
    AIContentGenerateRequest,
    AIContentRegenerateRequest,
    AudienceProfile,
    ContentType,
    PromptCategory,
    PromptTemplateCreateRequest,
    PromptTemplateStatus,
    PromptVariableRead,
    WritingStyle,
)
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
        _ = (system_prompt, user_prompt, temperature, max_tokens)
        self.__class__._call += 1
        suffix = self.__class__._call
        return type(
            "Result",
            (),
            {
                "content_by_type": {
                    key: f"Generated {key} content with #affiliate for model {model} #{suffix}"
                    for key in content_types
                },
                "model": model,
                "cost_usd": Decimal("0.001"),
                "latency_ms": 120,
            },
        )()


class _MockProviderFactory:
    def get_provider(
        self, *, provider_name: str, api_key: str, model: str, base_url: str | None
    ):
        _ = (provider_name, api_key, model, base_url)
        return _MockProvider()


def _create_template(service: AIContentService) -> int:
    template = service.create_template(
        payload=PromptTemplateCreateRequest(
            name="FB Template",
            category=PromptCategory.FACEBOOK,
            system_prompt="You are a marketer for {{platform}}",
            user_prompt=(
                "Create content for {{product_name}} with {{price}} discount {{discount}} "
                "for {{target_audience}} in {{language}}. Benefits: {{benefits}} Features: {{features}}"
            ),
            variables=[
                PromptVariableRead(name="platform"),
                PromptVariableRead(name="product_name"),
                PromptVariableRead(name="price"),
                PromptVariableRead(name="discount"),
                PromptVariableRead(name="target_audience"),
                PromptVariableRead(name="language"),
                PromptVariableRead(name="benefits"),
                PromptVariableRead(name="features"),
            ],
            temperature=Decimal("0.70"),
            max_tokens=700,
            version=1,
            status=PromptTemplateStatus.ACTIVE,
        ),
        created_by=1,
    )
    return template.id


def _seed_product(db_session: Session) -> int:
    repository = ProductRepository(db_session)
    product = repository.upsert_from_provider(
        source_url="https://shopee.co.id/product/1/9001",
        normalized_url="https://shopee.co.id/product/1/9001",
        marketplace="shopee",
        external_product_id="9001",
        fingerprint="fp-9001",
        payload=ProductPayload(
            marketplace="shopee",
            normalized_url="https://shopee.co.id/product/1/9001",
            external_product_id="9001",
            title="AI Product",
            price=Decimal("99.00"),
            original_price=Decimal("129.00"),
            discount="23%",
            rating=4.8,
            sold_count=90,
            images=["https://cdn.example.com/ai.jpg"],
            shop_name="AI Shop",
            category="Electronics",
            affiliate_url="https://shopee.co.id/product/1/9001",
        ),
        now=datetime.now(UTC),
        ttl_minutes=60,
        change_reason="import",
    )
    return product.id


def test_ai_content_generate_and_regenerate(db_session: Session) -> None:
    settings = get_settings()
    settings.ai_provider_encryption_key = "test-encryption-key"

    repository = AIContentRepository(db_session)
    product_id = _seed_product(db_session)

    service = AIContentService(
        ProductRepository(db_session),
        repository,
        _MockProviderFactory(),
        settings,
        InMemoryTTLCache(),
    )

    repository.upsert_provider_config(
        provider="openai",
        model="gpt-4o-mini",
        api_key="fake-key",
        encryption_key=settings.ai_provider_encryption_key,
        base_url=None,
        is_active=True,
    )

    _create_template(service)

    generated = asyncio.run(
        service.generate(
            payload=AIContentGenerateRequest(
                product_id=product_id,
                platform=PromptCategory.FACEBOOK,
                content_types=[ContentType.FACEBOOK_CAPTION, ContentType.CTA],
                style=WritingStyle.PROFESSIONAL,
                target_audience=AudienceProfile.ELECTRONICS,
                language="id",
                provider="openai",
                model="gpt-4o-mini",
                benefits=["Portable", "Durable"],
                features=["USB-C", "Fast charging"],
            ),
            created_by=1,
        )
    )
    assert generated.content_id > 0
    assert generated.version == 1

    regenerated = asyncio.run(
        service.regenerate(
            payload=AIContentRegenerateRequest(content_id=generated.content_id),
            created_by=1,
        )
    )
    assert regenerated.version == 2

    history = service.history(limit=10, offset=0, product_id=product_id)
    assert history.total == 1
    assert history.items[0].current_version == 2
