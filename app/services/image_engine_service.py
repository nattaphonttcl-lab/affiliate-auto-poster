from __future__ import annotations

import io
from dataclasses import dataclass
from hashlib import sha256

from PIL import Image

from app.core.cache import CacheBackend
from app.core.config import Settings
from app.core.exceptions import AppException
from app.models.ai_content import GeneratedContent
from app.repositories.ai_content_repository import AIContentRepository
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.image_engine_repository import ImageEngineRepository
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.image_engine import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageHistoryItemRead,
    ImageHistoryResponse,
    ImagePreviewRequest,
    ImagePreviewResponse,
    ImageTemplateCreateRequest,
    ImageTemplateRead,
    ImageTemplateStatus,
    ImageTemplateUpdateRequest,
    ImageType,
)
from app.services.image_providers import ImageProviderRegistry
from app.services.image_storage import ImageStorageBackend


@dataclass(frozen=True)
class _StoredOutputs:
    image_uri: str
    preview_uri: str
    thumbnail_uri: str
    width: int
    height: int


class ImageEngineService:
    def __init__(
        self,
        product_repository: ProductRepositoryProtocol,
        ai_repository: AIContentRepository,
        repository: ImageEngineRepository,
        provider_registry: ImageProviderRegistry,
        storage: ImageStorageBackend,
        settings: Settings,
        template_cache: CacheBackend,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._ai_repository = ai_repository
        self._repository = repository
        self._provider_registry = provider_registry
        self._storage = storage
        self._settings = settings
        self._template_cache = template_cache
        self._analytics_repository = analytics_repository

    def list_templates(
        self,
        *,
        image_type: ImageType | None,
        status: ImageTemplateStatus | None,
    ) -> list[ImageTemplateRead]:
        rows = self._repository.list_templates(image_type=image_type, status=status)
        return [ImageTemplateRead.model_validate(item) for item in rows]

    def create_template(
        self, *, payload: ImageTemplateCreateRequest, created_by: int
    ) -> ImageTemplateRead:
        item = self._repository.create_template(payload=payload, created_by=created_by)
        self._template_cache.delete(
            self._template_cache_key(payload.image_type, payload.version)
        )
        return ImageTemplateRead.model_validate(item)

    def update_template(
        self, *, template_id: int, payload: ImageTemplateUpdateRequest
    ) -> ImageTemplateRead:
        item = self._repository.update_template(
            template_id=template_id, payload=payload
        )
        if item is None:
            raise AppException(status_code=404, detail="Image template not found")

        self._template_cache.delete(
            self._template_cache_key(ImageType(item.image_type), item.version)
        )
        return ImageTemplateRead.model_validate(item)

    def delete_template(self, *, template_id: int) -> None:
        deleted = self._repository.delete_template(template_id=template_id)
        if not deleted:
            raise AppException(status_code=404, detail="Image template not found")

    async def generate(
        self,
        *,
        payload: ImageGenerateRequest,
        owner_user_id: int,
    ) -> ImageGenerateResponse:
        product = self._product_repository.get_by_id(payload.product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        template = self._resolve_template(
            image_type=payload.image_type,
            template_id=payload.template_id,
            version=payload.template_version,
        )

        caption = self._resolve_caption(
            product_id=payload.product_id,
            caption_content_id=payload.caption_content_id,
        )
        rendered_variables = self._build_variables(
            product_name=product.title,
            price=str(product.price),
            discount=product.discount or "",
            coupon=payload.variables.coupon or "",
            shop_name=product.shop_name or "",
            rating=str(product.rating or ""),
            sales=str(product.sold_count or ""),
            caption=caption,
            hashtags=payload.variables.hashtags or "",
            brand=payload.variables.brand or "",
            logo=payload.variables.logo or "",
            background=payload.variables.background or "",
        )
        prompt = self._render_prompt(template.layers, rendered_variables)

        provider_sequence = self._build_provider_sequence(
            primary=payload.provider.value, model=payload.model
        )
        attempt = await self._provider_registry.generate_with_failover(
            provider_sequence=provider_sequence,
            prompt=prompt,
            width=template.canvas_width,
            height=template.canvas_height,
            output_format=payload.output_format.value,
            variables=rendered_variables,
            model=payload.model,
        )

        self._quality_check(
            width=attempt.result.width,
            height=attempt.result.height,
            safe_area=template.safe_area,
            image_bytes=attempt.result.image_bytes,
        )

        file_hash = sha256(attempt.result.image_bytes).hexdigest()

        generated = self._repository.create_generated_image(
            product_id=payload.product_id,
            caption_source_id=payload.caption_content_id,
            template_id=template.id,
            image_type=payload.image_type.value,
            provider=attempt.provider_name,
            model=payload.model,
            prompt=attempt.result.prompt,
            owner_user_id=owner_user_id,
        )

        outputs = self._store_outputs(
            owner_user_id=owner_user_id,
            generated_image_id=generated.id,
            image_bytes=attempt.result.image_bytes,
            output_format=attempt.result.output_format,
            width=attempt.result.width,
            height=attempt.result.height,
        )

        version = self._repository.add_generated_image_version(
            generated_image_id=generated.id,
            provider=attempt.provider_name,
            model=payload.model,
            template_version=template.version,
            prompt=attempt.result.prompt,
            rendered_variables=rendered_variables,
            output_format=attempt.result.output_format,
            width=outputs.width,
            height=outputs.height,
            file_hash=file_hash,
            image_uri=outputs.image_uri,
            preview_uri=outputs.preview_uri,
            thumbnail_uri=outputs.thumbnail_uri,
            cost_usd=attempt.result.cost_usd,
            latency_ms=attempt.result.latency_ms,
            owner_user_id=owner_user_id,
        )
        self._repository.add_history(
            generated_image_id=generated.id,
            generated_image_version_id=version.id,
            action="generated",
            metadata={
                "provider": attempt.provider_name,
                "model": payload.model,
                "template_id": template.id,
            },
            owner_user_id=owner_user_id,
        )
        self._track_event(
            event_type="enterprise_image_generated",
            entity_id=generated.id,
            metadata={
                "provider": attempt.provider_name,
                "image_type": payload.image_type.value,
            },
        )

        return ImageGenerateResponse(
            generated_image_id=generated.id,
            version_id=version.id,
            version=version.version,
            provider=version.provider,
            model=version.model,
            template_version=version.template_version,
            output_format=version.output_format,
            image_uri=version.image_uri,
            preview_uri=version.preview_uri,
            thumbnail_uri=version.thumbnail_uri,
            cost_usd=version.cost_usd,
            latency_ms=version.latency_ms,
            created_at=version.created_at,
        )

    async def regenerate(
        self,
        *,
        generated_image_id: int,
        provider: str | None,
        model: str | None,
        owner_user_id: int,
    ) -> ImageGenerateResponse:
        generated = self._repository.get_generated_image(generated_image_id)
        if generated is None:
            raise AppException(status_code=404, detail="Generated image not found")

        template = self._repository.get_template_by_id(generated.template_id)
        if template is None:
            raise AppException(status_code=404, detail="Image template not found")

        latest = sorted(
            generated.versions, key=lambda item: item.version, reverse=True
        )[0]

        provider_name = provider or latest.provider
        model_name = model or latest.model

        provider_sequence = self._build_provider_sequence(
            primary=provider_name, model=model_name
        )
        attempt = await self._provider_registry.generate_with_failover(
            provider_sequence=provider_sequence,
            prompt=latest.prompt,
            width=latest.width,
            height=latest.height,
            output_format=latest.output_format,
            variables=latest.rendered_variables,
            model=model_name,
        )
        file_hash = sha256(attempt.result.image_bytes).hexdigest()
        if (
            self._repository.find_duplicate_version(
                generated_image_id=generated.id,
                file_hash=file_hash,
            )
            is not None
        ):
            variation_prompt = (
                f"{latest.prompt} variation_v{int(generated.current_version) + 1}"
            )
            attempt = await self._provider_registry.generate_with_failover(
                provider_sequence=provider_sequence,
                prompt=variation_prompt,
                width=latest.width,
                height=latest.height,
                output_format=latest.output_format,
                variables=latest.rendered_variables,
                model=model_name,
            )
            file_hash = sha256(attempt.result.image_bytes).hexdigest()
            if (
                self._repository.find_duplicate_version(
                    generated_image_id=generated.id,
                    file_hash=file_hash,
                )
                is not None
            ):
                raise AppException(status_code=422, detail="Duplicate image detected")

        outputs = self._store_outputs(
            owner_user_id=owner_user_id,
            generated_image_id=generated.id,
            image_bytes=attempt.result.image_bytes,
            output_format=attempt.result.output_format,
            width=attempt.result.width,
            height=attempt.result.height,
        )

        version = self._repository.add_generated_image_version(
            generated_image_id=generated.id,
            provider=attempt.provider_name,
            model=model_name,
            template_version=template.version,
            prompt=latest.prompt,
            rendered_variables=latest.rendered_variables,
            output_format=attempt.result.output_format,
            width=outputs.width,
            height=outputs.height,
            file_hash=file_hash,
            image_uri=outputs.image_uri,
            preview_uri=outputs.preview_uri,
            thumbnail_uri=outputs.thumbnail_uri,
            cost_usd=attempt.result.cost_usd,
            latency_ms=attempt.result.latency_ms,
            owner_user_id=owner_user_id,
        )
        self._repository.add_history(
            generated_image_id=generated.id,
            generated_image_version_id=version.id,
            action="regenerated",
            metadata={"provider": attempt.provider_name, "model": model_name},
            owner_user_id=owner_user_id,
        )

        return ImageGenerateResponse(
            generated_image_id=generated.id,
            version_id=version.id,
            version=version.version,
            provider=version.provider,
            model=version.model,
            template_version=version.template_version,
            output_format=version.output_format,
            image_uri=version.image_uri,
            preview_uri=version.preview_uri,
            thumbnail_uri=version.thumbnail_uri,
            cost_usd=version.cost_usd,
            latency_ms=version.latency_ms,
            created_at=version.created_at,
        )

    async def preview(
        self, *, payload: ImagePreviewRequest, owner_user_id: int
    ) -> ImagePreviewResponse:
        template = self._resolve_template(
            image_type=payload.image_type,
            template_id=payload.template_id,
            version=None,
        )
        product = self._product_repository.get_by_id(payload.product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        vars_map = self._build_variables(
            product_name=product.title,
            price=str(product.price),
            discount=product.discount or "",
            coupon=payload.variables.coupon or "",
            shop_name=product.shop_name or "",
            rating=str(product.rating or ""),
            sales=str(product.sold_count or ""),
            caption=payload.variables.caption or "Preview caption",
            hashtags=payload.variables.hashtags or "",
            brand=payload.variables.brand or "",
            logo=payload.variables.logo or "",
            background=payload.variables.background or "",
        )

        provider_sequence = [
            {"provider": "local_template", "api_key": None, "base_url": None}
        ]
        prompt = self._render_prompt(template.layers, vars_map)
        attempt = await self._provider_registry.generate_with_failover(
            provider_sequence=provider_sequence,
            prompt=prompt,
            width=template.canvas_width,
            height=template.canvas_height,
            output_format="png",
            variables=vars_map,
            model="local-preview",
        )

        outputs = self._store_outputs(
            owner_user_id=owner_user_id,
            generated_image_id=None,
            image_bytes=attempt.result.image_bytes,
            output_format=attempt.result.output_format,
            width=attempt.result.width,
            height=attempt.result.height,
            is_preview_only=True,
        )
        return ImagePreviewResponse(
            preview_uri=outputs.preview_uri,
            width=outputs.width,
            height=outputs.height,
        )

    def history(
        self, *, owner_user_id: int, limit: int, offset: int
    ) -> ImageHistoryResponse:
        rows = self._repository.list_history(
            owner_user_id=owner_user_id, limit=limit, offset=offset
        )
        total = self._repository.count_history(owner_user_id=owner_user_id)
        items = [
            ImageHistoryItemRead(
                generated_image_id=row.generated_image_id,
                version=row.version,
                image_type=self._repository.get_generated_image(
                    row.generated_image_id
                ).image_type,
                provider=row.provider,
                model=row.model,
                output_format=row.output_format,
                image_uri=row.image_uri,
                preview_uri=row.preview_uri,
                thumbnail_uri=row.thumbnail_uri,
                cost_usd=row.cost_usd,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return ImageHistoryResponse(
            total=total, limit=limit, offset=offset, items=items
        )

    def _resolve_template(
        self, *, image_type: ImageType, template_id: int | None, version: int | None
    ):
        if template_id is not None:
            template = self._repository.get_template_by_id(template_id)
            if template is None:
                raise AppException(status_code=404, detail="Image template not found")
            return template

        cache_key = self._template_cache_key(image_type, version)
        cached = self._template_cache.get(cache_key)
        if cached is not None:
            item = self._repository.get_template_by_id(int(cached))
            if item is not None:
                return item

        item = self._repository.get_latest_template(
            image_type=image_type, version=version
        )
        if item is None:
            raise AppException(status_code=404, detail="No active image template found")
        self._template_cache.set(
            cache_key,
            str(item.id),
            ttl_seconds=self._settings.image_template_cache_ttl_seconds,
        )
        return item

    def _template_cache_key(self, image_type: ImageType, version: int | None) -> str:
        suffix = "latest" if version is None else str(version)
        return f"image-template:{image_type.value}:{suffix}"

    def _build_variables(self, **kwargs: str) -> dict[str, str]:
        return {key: (value or "") for key, value in kwargs.items()}

    def _render_prompt(
        self,
        layers: list[dict[str, str | int | float | bool]],
        variables: dict[str, str],
    ) -> str:
        base = (
            " | ".join(str(layer.get("name", "layer")) for layer in layers) or "image"
        )
        prompt = f"Generate marketing image with layers: {base}."
        for key, value in variables.items():
            prompt += f" {key}={value};"
        return prompt

    def _resolve_caption(
        self, *, product_id: int, caption_content_id: int | None
    ) -> str:
        if caption_content_id is not None:
            row = self._ai_repository.get_content_by_id(caption_content_id)
            if row is None:
                raise AppException(status_code=404, detail="Caption content not found")
            latest = sorted(row.versions, key=lambda item: item.version, reverse=True)[
                0
            ]
            return self._pick_caption_text(latest.generated_text)

        candidates = self._ai_repository.list_content_history(
            limit=1, offset=0, product_id=product_id
        )
        if not candidates:
            return ""
        latest_row: GeneratedContent = candidates[0]
        latest = sorted(
            latest_row.versions, key=lambda item: item.version, reverse=True
        )[0]
        return self._pick_caption_text(latest.generated_text)

    def _pick_caption_text(self, generated_text: dict[str, str]) -> str:
        for key in ("facebook_caption", "tiktok_caption", "short_description"):
            if key in generated_text and generated_text[key].strip():
                return generated_text[key].strip()
        for value in generated_text.values():
            if value.strip():
                return value.strip()
        return ""

    def _build_provider_sequence(
        self, *, primary: str, model: str
    ) -> list[dict[str, str | None]]:
        order = [
            item.strip()
            for item in self._settings.image_provider_failover_order.split(",")
            if item.strip()
        ]
        normalized = [primary] + [item for item in order if item != primary]

        sequence: list[dict[str, str | None]] = []
        for provider in normalized:
            config = self._repository.get_active_provider_config(
                provider=provider, model=model
            )
            api_key: str | None = None
            base_url: str | None = None
            if config is not None:
                api_key = self._repository.decrypt_provider_api_key(
                    config=config,
                    encryption_key=self._settings.image_provider_encryption_key,
                )
                base_url = config.base_url
            else:
                env_map = {
                    "openai": self._settings.openai_api_key,
                    "google_imagen": self._settings.google_imagen_api_key,
                    "stability_ai": self._settings.stability_ai_api_key,
                    "flux": self._settings.flux_api_key,
                    "local_template": None,
                }
                api_key = env_map.get(provider)

            sequence.append(
                {"provider": provider, "api_key": api_key, "base_url": base_url}
            )
        return sequence

    def _quality_check(
        self,
        *,
        width: int,
        height: int,
        safe_area: dict[str, int],
        image_bytes: bytes,
    ) -> None:
        if (
            width < self._settings.image_min_resolution_width
            or height < self._settings.image_min_resolution_height
        ):
            raise AppException(
                status_code=422, detail="Image resolution below minimum requirement"
            )

        if safe_area.get("x", 0) < 0 or safe_area.get("y", 0) < 0:
            raise AppException(status_code=422, detail="Invalid logo safe area")

        try:
            Image.open(io.BytesIO(image_bytes)).verify()
        except Exception as exc:
            raise AppException(
                status_code=422, detail="Generated image is corrupted"
            ) from exc

    def _store_outputs(
        self,
        *,
        owner_user_id: int,
        generated_image_id: int | None,
        image_bytes: bytes,
        output_format: str,
        width: int,
        height: int,
        is_preview_only: bool = False,
    ) -> _StoredOutputs:
        base_id = str(generated_image_id or f"preview-{owner_user_id}")
        ext = output_format.lower()
        image_key = f"images/{owner_user_id}/{base_id}/image.{ext}"
        preview_key = f"images/{owner_user_id}/{base_id}/preview.jpg"
        thumbnail_key = f"images/{owner_user_id}/{base_id}/thumb.jpg"

        image_uri = self._storage.save_bytes(
            key=image_key,
            payload=image_bytes,
            content_type=f"image/{ext}",
        )

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        preview = image.copy()
        preview.thumbnail((960, 960))
        thumb = image.copy()
        thumb.thumbnail((320, 320))

        preview_buffer = io.BytesIO()
        preview.save(preview_buffer, format="JPEG", optimize=True, quality=85)

        thumb_buffer = io.BytesIO()
        thumb.save(thumb_buffer, format="JPEG", optimize=True, quality=75)

        preview_uri = self._storage.save_bytes(
            key=preview_key,
            payload=preview_buffer.getvalue(),
            content_type="image/jpeg",
        )
        if is_preview_only:
            thumbnail_uri = preview_uri
        else:
            thumbnail_uri = self._storage.save_bytes(
                key=thumbnail_key,
                payload=thumb_buffer.getvalue(),
                content_type="image/jpeg",
            )

        return _StoredOutputs(
            image_uri=image_uri,
            preview_uri=preview_uri,
            thumbnail_uri=thumbnail_uri,
            width=width,
            height=height,
        )

    def _track_event(
        self,
        *,
        event_type: str,
        entity_id: int,
        metadata: dict[str, str | int | float | bool | None],
    ) -> None:
        if self._analytics_repository is None:
            return
        self._analytics_repository.record_event(
            event_type=event_type,
            entity_type="generated_image",
            entity_id=entity_id,
            metadata=metadata,
        )
