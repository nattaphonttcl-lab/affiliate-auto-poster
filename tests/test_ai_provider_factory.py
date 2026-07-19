import pytest

from app.core.exceptions import AppException
from app.services.ai_providers import ProviderFactory


def test_provider_factory_returns_cached_instance() -> None:
    factory = ProviderFactory()

    first = factory.get_provider(
        provider_name="openai",
        api_key="k",
        model="gpt-4o-mini",
        base_url=None,
    )
    second = factory.get_provider(
        provider_name="openai",
        api_key="k",
        model="gpt-4o-mini",
        base_url=None,
    )

    assert first is second


def test_provider_factory_rejects_unsupported_provider() -> None:
    factory = ProviderFactory()

    with pytest.raises(AppException):
        factory.get_provider(
            provider_name="unknown",
            api_key="k",
            model="x",
            base_url=None,
        )
