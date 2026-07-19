from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.credentials import decrypt_secret, encrypt_secret
from app.models.image_generation import (
    GeneratedImage,
    GeneratedImageVersion,
    ImageHistory,
    ImageProviderConfig,
    ImageTemplate,
)
from app.schemas.image_engine import (
    ImageTemplateCreateRequest,
    ImageTemplateStatus,
    ImageTemplateUpdateRequest,
    ImageType,
)


class ImageEngineRepositoryProtocol(Protocol):
    def create_template(
        self, *, payload: ImageTemplateCreateRequest, created_by: int
    ) -> ImageTemplate: ...

    def list_templates(
        self, *, image_type: ImageType | None, status: ImageTemplateStatus | None
    ) -> list[ImageTemplate]: ...

    def get_template_by_id(self, template_id: int) -> ImageTemplate | None: ...

    def get_latest_template(
        self, *, image_type: ImageType, version: int | None = None
    ) -> ImageTemplate | None: ...

    def update_template(
        self, *, template_id: int, payload: ImageTemplateUpdateRequest
    ) -> ImageTemplate | None: ...

    def delete_template(self, *, template_id: int) -> bool: ...


class ImageEngineRepository(ImageEngineRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def _image_query(self):
        return select(GeneratedImage).options(joinedload(GeneratedImage.versions))

    def create_template(
        self, *, payload: ImageTemplateCreateRequest, created_by: int
    ) -> ImageTemplate:
        template = ImageTemplate(
            name=payload.name,
            image_type=payload.image_type.value,
            canvas_width=payload.canvas_width,
            canvas_height=payload.canvas_height,
            safe_area=payload.safe_area,
            background=payload.background,
            layers=payload.layers,
            fonts=payload.fonts,
            colors=payload.colors,
            logo_position=payload.logo_position,
            watermark=payload.watermark,
            overlay=payload.overlay,
            dynamic_variables=payload.dynamic_variables,
            version=payload.version,
            status=payload.status.value,
            created_by=created_by,
        )
        self._db.add(template)
        self._db.commit()
        self._db.refresh(template)
        return template

    def list_templates(
        self,
        *,
        image_type: ImageType | None,
        status: ImageTemplateStatus | None,
    ) -> list[ImageTemplate]:
        stmt = select(ImageTemplate).order_by(ImageTemplate.updated_at.desc())
        if image_type is not None:
            stmt = stmt.where(ImageTemplate.image_type == image_type.value)
        if status is not None:
            stmt = stmt.where(ImageTemplate.status == status.value)
        return list(self._db.scalars(stmt))

    def get_template_by_id(self, template_id: int) -> ImageTemplate | None:
        stmt = select(ImageTemplate).where(ImageTemplate.id == template_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_latest_template(
        self, *, image_type: ImageType, version: int | None = None
    ) -> ImageTemplate | None:
        stmt = select(ImageTemplate).where(
            ImageTemplate.image_type == image_type.value,
            ImageTemplate.status == ImageTemplateStatus.ACTIVE.value,
        )
        if version is not None:
            stmt = stmt.where(ImageTemplate.version == version)
        stmt = stmt.order_by(
            ImageTemplate.version.desc(), ImageTemplate.updated_at.desc()
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def update_template(
        self, *, template_id: int, payload: ImageTemplateUpdateRequest
    ) -> ImageTemplate | None:
        template = self.get_template_by_id(template_id)
        if template is None:
            return None

        data = payload.model_dump(exclude_unset=True)
        if "status" in data and data["status"] is not None:
            data["status"] = data["status"].value
        for key, value in data.items():
            setattr(template, key, value)

        self._db.add(template)
        self._db.commit()
        self._db.refresh(template)
        return template

    def delete_template(self, *, template_id: int) -> bool:
        template = self.get_template_by_id(template_id)
        if template is None:
            return False
        self._db.delete(template)
        self._db.commit()
        return True

    def get_active_provider_config(
        self, *, provider: str, model: str
    ) -> ImageProviderConfig | None:
        stmt = select(ImageProviderConfig).where(
            ImageProviderConfig.provider == provider,
            ImageProviderConfig.model == model,
            ImageProviderConfig.is_active.is_(True),
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def upsert_provider_config(
        self,
        *,
        provider: str,
        model: str,
        api_key: str,
        encryption_key: str,
        base_url: str | None,
        is_active: bool,
    ) -> ImageProviderConfig:
        config = self.get_active_provider_config(provider=provider, model=model)
        encrypted = encrypt_secret(plaintext=api_key, secret_key=encryption_key)

        if config is None:
            config = ImageProviderConfig(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key_encrypted=encrypted,
                is_active=is_active,
            )
        else:
            config.base_url = base_url
            config.api_key_encrypted = encrypted
            config.is_active = is_active

        self._db.add(config)
        self._db.commit()
        self._db.refresh(config)
        return config

    def decrypt_provider_api_key(
        self, *, config: ImageProviderConfig, encryption_key: str
    ) -> str:
        return decrypt_secret(
            ciphertext=config.api_key_encrypted, secret_key=encryption_key
        )

    def create_generated_image(
        self,
        *,
        product_id: int,
        caption_source_id: int | None,
        template_id: int,
        image_type: str,
        provider: str,
        model: str,
        prompt: str,
        owner_user_id: int,
    ) -> GeneratedImage:
        item = GeneratedImage(
            product_id=product_id,
            caption_source_id=caption_source_id,
            template_id=template_id,
            image_type=image_type,
            provider=provider,
            model=model,
            current_version=1,
            prompt=prompt,
            owner_user_id=owner_user_id,
            total_cost_usd=Decimal("0"),
        )
        self._db.add(item)
        self._db.flush()
        return item

    def get_generated_image(self, generated_image_id: int) -> GeneratedImage | None:
        stmt = self._image_query().where(GeneratedImage.id == generated_image_id)
        return self._db.execute(stmt).unique().scalar_one_or_none()

    def add_generated_image_version(
        self,
        *,
        generated_image_id: int,
        provider: str,
        model: str,
        template_version: int,
        prompt: str,
        rendered_variables: dict[str, str],
        output_format: str,
        width: int,
        height: int,
        file_hash: str,
        image_uri: str,
        preview_uri: str,
        thumbnail_uri: str,
        cost_usd: Decimal,
        latency_ms: int,
        owner_user_id: int,
    ) -> GeneratedImageVersion:
        generated = self.get_generated_image(generated_image_id)
        if generated is None:
            raise ValueError("generated image not found")

        next_version = 1
        if generated.versions:
            next_version = max(item.version for item in generated.versions) + 1

        version = GeneratedImageVersion(
            generated_image_id=generated_image_id,
            version=next_version,
            provider=provider,
            model=model,
            template_version=template_version,
            prompt=prompt,
            rendered_variables=rendered_variables,
            output_format=output_format,
            width=width,
            height=height,
            file_hash=file_hash,
            image_uri=image_uri,
            preview_uri=preview_uri,
            thumbnail_uri=thumbnail_uri,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            owner_user_id=owner_user_id,
        )
        generated.current_version = next_version
        generated.provider = provider
        generated.model = model
        generated.total_cost_usd = Decimal(generated.total_cost_usd) + Decimal(cost_usd)

        self._db.add(version)
        self._db.add(generated)
        self._db.commit()
        self._db.refresh(version)
        return version

    def add_history(
        self,
        *,
        generated_image_id: int,
        generated_image_version_id: int | None,
        action: str,
        metadata: dict[str, str | int | float | bool | None],
        owner_user_id: int,
    ) -> ImageHistory:
        history = ImageHistory(
            generated_image_id=generated_image_id,
            generated_image_version_id=generated_image_version_id,
            action=action,
            event_metadata=metadata,
            owner_user_id=owner_user_id,
        )
        self._db.add(history)
        self._db.commit()
        self._db.refresh(history)
        return history

    def find_duplicate_version(
        self, *, generated_image_id: int, file_hash: str
    ) -> GeneratedImageVersion | None:
        stmt = select(GeneratedImageVersion).where(
            GeneratedImageVersion.generated_image_id == generated_image_id,
            GeneratedImageVersion.file_hash == file_hash,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_history(
        self,
        *,
        owner_user_id: int,
        limit: int,
        offset: int,
    ) -> list[GeneratedImageVersion]:
        stmt = (
            select(GeneratedImageVersion)
            .where(GeneratedImageVersion.owner_user_id == owner_user_id)
            .order_by(GeneratedImageVersion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def count_history(self, *, owner_user_id: int) -> int:
        stmt = select(func.count(GeneratedImageVersion.id)).where(
            GeneratedImageVersion.owner_user_id == owner_user_id
        )
        return int(self._db.scalar(stmt) or 0)
