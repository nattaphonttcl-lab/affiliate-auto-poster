from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from app.core.exceptions import AppException


@dataclass(frozen=True)
class PublishPayload:
    caption: str
    hashtags: list[str]
    mentions: list[str]
    cta: str | None
    affiliate_link: str | None
    media_uris: list[str]
    thumbnail_uri: str | None
    alt_text: str | None
    idempotency_key: str


@dataclass(frozen=True)
class PublishResult:
    external_post_id: str
    status: str
    response_payload: dict[str, str | int | float | bool | None]
    latency_ms: int


class SocialProvider(Protocol):
    def publish(
        self,
        *,
        account_identifier: str,
        post_type: str,
        payload: PublishPayload,
        credentials: dict[str, str | None],
    ) -> PublishResult: ...


class _BaseProvider:
    provider_name = "base"

    def publish(
        self,
        *,
        account_identifier: str,
        post_type: str,
        payload: PublishPayload,
        credentials: dict[str, str | None],
    ) -> PublishResult:
        access = credentials.get("access_token")
        if not access:
            raise AppException(status_code=422, detail="Missing platform credential")

        seed = (
            f"{self.provider_name}:{account_identifier}:{post_type}:"
            f"{payload.idempotency_key}:{payload.caption}:{'|'.join(payload.media_uris)}"
        )
        digest = sha256(seed.encode("utf-8")).hexdigest()[:16]
        return PublishResult(
            external_post_id=f"{self.provider_name}-{digest}",
            status="published",
            response_payload={
                "provider": self.provider_name,
                "post_type": post_type,
                "account_identifier": account_identifier,
                "external_post_id": f"{self.provider_name}-{digest}",
                "published_at": datetime.now(UTC).isoformat(),
            },
            latency_ms=120,
        )


class FacebookProvider(_BaseProvider):
    provider_name = "facebook"


class FacebookPageProvider(_BaseProvider):
    provider_name = "facebook_page"


class InstagramProvider(_BaseProvider):
    provider_name = "instagram"


class ThreadsProvider(_BaseProvider):
    provider_name = "threads"


class TikTokProvider(_BaseProvider):
    provider_name = "tiktok"


class YouTubeShortsProvider(_BaseProvider):
    provider_name = "youtube_shorts"


class ShopeeVideoProvider(_BaseProvider):
    provider_name = "shopee_video"


class ProviderFactory:
    def __init__(self) -> None:
        self._cache: dict[str, SocialProvider] = {}

    def get_provider(self, platform: str) -> SocialProvider:
        key = platform.strip().lower()
        if key in self._cache:
            return self._cache[key]

        mapping: dict[str, type[_BaseProvider]] = {
            "facebook": FacebookProvider,
            "facebook_page": FacebookPageProvider,
            "instagram": InstagramProvider,
            "threads": ThreadsProvider,
            "tiktok": TikTokProvider,
            "youtube_shorts": YouTubeShortsProvider,
            "shopee_video": ShopeeVideoProvider,
        }
        provider_cls = mapping.get(key)
        if provider_cls is None:
            raise AppException(
                status_code=422, detail=f"Unsupported platform: {platform}"
            )

        provider = provider_cls()
        self._cache[key] = provider
        return provider


class ProviderRegistry:
    def __init__(self, factory: ProviderFactory) -> None:
        self._factory = factory

    def publish_with_failover(
        self,
        *,
        provider_sequence: list[str],
        account_identifier: str,
        post_type: str,
        payload: PublishPayload,
        credentials: dict[str, str | None],
    ) -> tuple[str, PublishResult]:
        last_error: AppException | None = None
        for provider_name in provider_sequence:
            try:
                provider = self._factory.get_provider(provider_name)
            except AppException as exc:
                last_error = exc
                continue
            try:
                result = provider.publish(
                    account_identifier=account_identifier,
                    post_type=post_type,
                    payload=payload,
                    credentials=credentials,
                )
                return provider_name, result
            except AppException as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise AppException(status_code=500, detail="No provider available")
