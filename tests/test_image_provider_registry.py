import asyncio

from app.services.image_providers import ImageProviderFactory, ImageProviderRegistry


def test_provider_registry_failover_to_local_template() -> None:
    factory = ImageProviderFactory()
    registry = ImageProviderRegistry(factory=factory)

    result = asyncio.run(
        registry.generate_with_failover(
            provider_sequence=[
                {"provider": "flux", "api_key": None, "base_url": None},
                {"provider": "local_template", "api_key": None, "base_url": None},
            ],
            prompt="Generate promo image",
            width=1080,
            height=1080,
            output_format="png",
            variables={"product_name": "Headset", "price": "99"},
            model="test-model",
        )
    )

    assert result.provider_name == "local_template"
    assert result.result.width == 1080
    assert result.result.height == 1080
    assert result.result.image_bytes
