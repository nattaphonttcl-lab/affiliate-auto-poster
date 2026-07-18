from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.core.exceptions import AppException
from app.schemas.product import ProductPayload
from app.services.url_normalizer import URLNormalizer
from app.utils.shopee_parser import ShopeeProductParser
from app.utils.shopee_validator import ShopeeProductValidator


class MarketplaceProvider:
    marketplace: str

    def __init__(self, *, normalizer: URLNormalizer | None = None) -> None:
        self._normalizer = normalizer or URLNormalizer()

    def supports(self, url: str) -> bool:
        raise NotImplementedError

    def normalize_url(self, url: str) -> str:
        return self._normalizer.normalize(url)

    def extract_product_id(self, normalized_url: str) -> str | None:
        return None

    def fetch_product(self, normalized_url: str) -> ProductPayload:
        raise NotImplementedError


class ShopeeProvider(MarketplaceProvider):
    marketplace = "shopee"

    def __init__(
        self, *, parser: ShopeeProductParser, validator: ShopeeProductValidator
    ) -> None:
        super().__init__()
        self._parser = parser
        self._validator = validator

    def supports(self, url: str) -> bool:
        parsed = self._normalizer.parse_and_validate_public_url(url)
        host = (parsed.hostname or "").lower()
        return "shopee." in host

    def extract_product_id(self, normalized_url: str) -> str | None:
        patterns = [
            r"/product/\d+/(\d+)",
            r"/i\.\d+\.(\d+)",
            r"itemid=(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized_url)
            if match:
                return match.group(1)
        return None

    def fetch_product(self, normalized_url: str) -> ProductPayload:
        self._validator.validate_url(normalized_url)
        try:
            payload = self._parser.parse(normalized_url)
        except httpx.TimeoutException as exc:
            raise AppException(
                status_code=504, detail="Marketplace provider timeout"
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise AppException(
                    status_code=429, detail="Marketplace rate limit exceeded"
                ) from exc
            raise AppException(
                status_code=503, detail="Marketplace provider unavailable"
            ) from exc
        except httpx.HTTPError as exc:
            raise AppException(
                status_code=503, detail="Marketplace provider unavailable"
            ) from exc
        self._validator.validate_payload(payload)
        payload.marketplace = self.marketplace
        payload.external_product_id = self.extract_product_id(normalized_url)
        payload.normalized_url = normalized_url
        return payload


class LazadaProvider(MarketplaceProvider):
    marketplace = "lazada"

    def supports(self, url: str) -> bool:
        parsed = self._normalizer.parse_and_validate_public_url(url)
        host = (parsed.hostname or "").lower()
        return "lazada." in host

    def fetch_product(self, normalized_url: str) -> ProductPayload:
        raise AppException(
            status_code=422, detail="Marketplace not supported yet: lazada"
        )


class TikTokShopProvider(MarketplaceProvider):
    marketplace = "tiktokshop"

    def supports(self, url: str) -> bool:
        parsed = self._normalizer.parse_and_validate_public_url(url)
        host = (parsed.hostname or "").lower()
        return "tiktok." in host or "tiktokshop." in host

    def fetch_product(self, normalized_url: str) -> ProductPayload:
        raise AppException(
            status_code=422, detail="Marketplace not supported yet: tiktokshop"
        )


@dataclass
class MarketplaceProviderRegistry:
    providers: list[MarketplaceProvider]

    def resolve(self, url: str) -> MarketplaceProvider:
        for provider in self.providers:
            if provider.supports(url):
                return provider
        raise AppException(status_code=422, detail="Marketplace not supported")

    def get_by_marketplace(self, marketplace: str) -> MarketplaceProvider:
        for provider in self.providers:
            if provider.marketplace == marketplace:
                return provider
        raise AppException(status_code=422, detail="Marketplace not supported")
