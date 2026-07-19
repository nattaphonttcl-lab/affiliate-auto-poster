from __future__ import annotations

import io
import time
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.exceptions import AppException


@dataclass(frozen=True)
class ImageProviderResult:
    image_bytes: bytes
    output_format: str
    width: int
    height: int
    prompt: str
    cost_usd: Decimal
    latency_ms: int


class ImageProvider(Protocol):
    provider_name: str

    async def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ImageProviderResult: ...


class _BaseProvider:
    provider_name: str

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout_seconds


class LocalTemplateProvider(_BaseProvider):
    provider_name = "local_template"

    async def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ImageProviderResult:
        _ = model
        start = time.perf_counter()

        image = Image.new("RGB", (width, height), color=(245, 246, 250))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, int(height * 0.22)), fill=(32, 48, 78))

        title = variables.get("product_name", "Product")
        price = variables.get("price", "-")
        shop_name = variables.get("shop_name", "Shop")
        caption = variables.get("caption", "")

        title_font = self._load_font(32)
        body_font = self._load_font(24)

        draw.text((28, 24), title[:60], fill=(255, 255, 255), font=title_font)
        draw.text(
            (28, int(height * 0.30)),
            f"Price: {price}",
            fill=(14, 17, 30),
            font=body_font,
        )
        draw.text(
            (28, int(height * 0.42)),
            f"Shop: {shop_name}",
            fill=(14, 17, 30),
            font=body_font,
        )
        draw.text(
            (28, int(height * 0.56)), caption[:180], fill=(32, 46, 70), font=body_font
        )
        fingerprint = sha256(prompt.encode("utf-8")).hexdigest()[:8]
        draw.text(
            (28, int(height * 0.90)),
            f"v:{fingerprint}",
            fill=(120, 128, 138),
            font=self._load_font(18),
        )

        output = io.BytesIO()
        fmt = output_format.upper()
        if fmt == "JPG":
            fmt = "JPEG"
        image.save(output, format=fmt)

        latency_ms = int((time.perf_counter() - start) * 1000)
        return ImageProviderResult(
            image_bytes=output.getvalue(),
            output_format=output_format,
            width=width,
            height=height,
            prompt=prompt,
            cost_usd=Decimal("0"),
            latency_ms=latency_ms,
        )

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        for candidate in ("DejaVuSans-Bold.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()


class OpenAIImageProvider(_BaseProvider):
    provider_name = "openai"

    async def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ImageProviderResult:
        _ = variables
        if not self._api_key:
            raise AppException(
                status_code=503, detail="OpenAI image provider key is not configured"
            )

        endpoint = (
            self._base_url or "https://api.openai.com"
        ) + "/v1/images/generations"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": model, "prompt": prompt, "size": f"{width}x{height}"},
            )
        if response.status_code >= 400:
            raise AppException(
                status_code=503, detail="OpenAI image provider unavailable"
            )

        # External providers may return URLs/base64. We keep network integration optional and deterministic in tests.
        raise AppException(
            status_code=503, detail="OpenAI image parsing is not configured"
        )


class GoogleImagenProvider(_BaseProvider):
    provider_name = "google_imagen"

    async def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ImageProviderResult:
        _ = (prompt, width, height, output_format, variables, model)
        raise AppException(
            status_code=503, detail="Google Imagen provider is not configured"
        )


class StabilityAIProvider(_BaseProvider):
    provider_name = "stability_ai"

    async def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ImageProviderResult:
        _ = (prompt, width, height, output_format, variables, model)
        raise AppException(
            status_code=503, detail="Stability AI provider is not configured"
        )


class FluxProvider(_BaseProvider):
    provider_name = "flux"

    async def generate_image(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ImageProviderResult:
        _ = (prompt, width, height, output_format, variables, model)
        raise AppException(status_code=503, detail="Flux provider is not configured")


class ImageProviderFactory:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, str], ImageProvider] = {}

    def get_provider(
        self,
        *,
        provider_name: str,
        api_key: str | None,
        model: str,
        base_url: str | None,
    ) -> ImageProvider:
        cache_key = (provider_name, model, base_url or "")
        if cache_key in self._cache:
            return self._cache[cache_key]

        if provider_name == "local_template":
            provider: ImageProvider = LocalTemplateProvider(api_key=None, base_url=None)
        elif provider_name == "openai":
            provider = OpenAIImageProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "google_imagen":
            provider = GoogleImagenProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "stability_ai":
            provider = StabilityAIProvider(api_key=api_key, base_url=base_url)
        elif provider_name == "flux":
            provider = FluxProvider(api_key=api_key, base_url=base_url)
        else:
            raise AppException(
                status_code=422, detail="Image provider is not supported"
            )

        self._cache[cache_key] = provider
        return provider


@dataclass(frozen=True)
class ProviderAttemptResult:
    provider_name: str
    result: ImageProviderResult


class ImageProviderRegistry:
    def __init__(self, *, factory: ImageProviderFactory) -> None:
        self._factory = factory

    async def generate_with_failover(
        self,
        *,
        provider_sequence: list[dict[str, str | None]],
        prompt: str,
        width: int,
        height: int,
        output_format: str,
        variables: dict[str, str],
        model: str,
    ) -> ProviderAttemptResult:
        errors: list[str] = []
        for spec in provider_sequence:
            name = str(spec["provider"])
            api_key = spec.get("api_key")
            base_url = spec.get("base_url")
            provider = self._factory.get_provider(
                provider_name=name,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )
            try:
                result = await provider.generate_image(
                    prompt=prompt,
                    width=width,
                    height=height,
                    output_format=output_format,
                    variables=variables,
                    model=model,
                )
                return ProviderAttemptResult(provider_name=name, result=result)
            except AppException as exc:
                errors.append(f"{name}: {exc.detail}")

        raise AppException(
            status_code=503,
            detail=f"All image providers failed ({'; '.join(errors)})",
        )


def hash_image_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()
