from app.core.exceptions import AppException
from app.services.social_providers import (
    ProviderFactory,
    ProviderRegistry,
    PublishPayload,
)


def _payload() -> PublishPayload:
    return PublishPayload(
        caption="Test caption",
        hashtags=["#sale"],
        mentions=["@shop"],
        cta="Buy now",
        affiliate_link="https://example.com/a",
        media_uris=["https://cdn.example.com/img.jpg"],
        thumbnail_uri=None,
        alt_text="alt",
        idempotency_key="idem-key-123",
    )


def test_provider_registry_failover_works() -> None:
    registry = ProviderRegistry(factory=ProviderFactory())

    provider, result = registry.publish_with_failover(
        provider_sequence=["unknown", "facebook"],
        account_identifier="acct-1",
        post_type="facebook_feed",
        payload=_payload(),
        credentials={"access_token": "token", "refresh_token": None},
    )

    assert provider == "facebook"
    assert result.status == "published"
    assert result.external_post_id.startswith("facebook-")


def test_provider_requires_credentials() -> None:
    registry = ProviderRegistry(factory=ProviderFactory())

    try:
        registry.publish_with_failover(
            provider_sequence=["facebook"],
            account_identifier="acct-1",
            post_type="facebook_feed",
            payload=_payload(),
            credentials={"access_token": None, "refresh_token": None},
        )
        assert False, "expected AppException"
    except AppException as exc:
        assert exc.status_code == 422
