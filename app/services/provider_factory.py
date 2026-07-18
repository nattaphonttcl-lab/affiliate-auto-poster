from __future__ import annotations

from app.services.marketplace_provider import (
    LazadaProvider,
    MarketplaceProviderRegistry,
    ShopeeProvider,
    TikTokShopProvider,
)
from app.utils.shopee_parser import ShopeeProductParser
from app.utils.shopee_validator import ShopeeProductValidator


def build_provider_registry(
    *, shopee_parser: ShopeeProductParser, shopee_validator: ShopeeProductValidator
) -> MarketplaceProviderRegistry:
    return MarketplaceProviderRegistry(
        providers=[
            ShopeeProvider(parser=shopee_parser, validator=shopee_validator),
            LazadaProvider(),
            TikTokShopProvider(),
        ]
    )
