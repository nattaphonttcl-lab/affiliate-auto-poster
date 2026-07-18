from decimal import Decimal

import pytest

from app.core.exceptions import AppException
from app.schemas.product import ProductPayload
from app.services.marketplace_provider import (
    MarketplaceProviderRegistry,
    ShopeeProvider,
)
from app.services.provider_factory import build_provider_registry
from app.services.url_normalizer import URLNormalizer


class _Parser:
    def parse(self, url: str) -> ProductPayload:
        return ProductPayload(
            marketplace="shopee",
            normalized_url=url,
            external_product_id="123",
            title="Test",
            price=Decimal("10.00"),
            images=["https://cdn.example.com/p.png"],
            affiliate_url=url,
        )


class _Validator:
    def validate_url(self, _: str) -> None:
        return None

    def validate_payload(self, _: ProductPayload) -> None:
        return None


def test_provider_registry_resolves_shopee() -> None:
    registry = MarketplaceProviderRegistry(
        providers=[ShopeeProvider(parser=_Parser(), validator=_Validator())]
    )

    provider = registry.resolve("https://shopee.co.id/product/1/2")
    assert provider.marketplace == "shopee"


def test_provider_registry_rejects_unsupported_marketplace() -> None:
    registry = MarketplaceProviderRegistry(
        providers=[ShopeeProvider(parser=_Parser(), validator=_Validator())]
    )

    with pytest.raises(AppException):
        registry.resolve("https://example.com/item/1")


def test_url_normalizer_rejects_localhost_and_private_ip() -> None:
    normalizer = URLNormalizer()

    with pytest.raises(AppException):
        normalizer.normalize("http://localhost/internal")

    with pytest.raises(AppException):
        normalizer.normalize("http://10.0.0.8/private")


def test_shopee_provider_extract_product_id_patterns() -> None:
    provider = ShopeeProvider(parser=_Parser(), validator=_Validator())

    assert provider.extract_product_id("https://shopee.co.id/product/123/456") == "456"
    assert provider.extract_product_id("https://shopee.co.id/i.123.999") == "999"


def test_provider_factory_builds_expected_marketplaces() -> None:
    registry = build_provider_registry(
        shopee_parser=_Parser(),
        shopee_validator=_Validator(),
    )

    marketplaces = {provider.marketplace for provider in registry.providers}
    assert marketplaces == {"shopee", "lazada", "tiktokshop"}
