from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.credentials import decrypt_secret, encrypt_secret
from app.models.ai_content import (
    AIProviderConfig,
    GeneratedContent,
    GeneratedContentVersion,
    PromptTemplate,
    PromptVariable,
)
from app.schemas.ai_content import (
    PromptCategory,
    PromptTemplateCreateRequest,
    PromptTemplateStatus,
    PromptTemplateUpdateRequest,
)


class AIContentRepositoryProtocol(Protocol):
    def create_template(
        self, *, payload: PromptTemplateCreateRequest, created_by: int
    ) -> PromptTemplate: ...

    def list_templates(
        self, *, category: PromptCategory | None, status: PromptTemplateStatus | None
    ) -> list[PromptTemplate]: ...

    def get_template_by_id(self, template_id: int) -> PromptTemplate | None: ...

    def get_latest_template(
        self, *, category: PromptCategory, version: int | None = None
    ) -> PromptTemplate | None: ...

    def update_template(
        self, *, template_id: int, payload: PromptTemplateUpdateRequest
    ) -> PromptTemplate | None: ...

    def delete_template(self, *, template_id: int) -> bool: ...

    def get_active_provider_config(
        self, *, provider: str, model: str
    ) -> AIProviderConfig | None: ...

    def upsert_provider_config(
        self,
        *,
        provider: str,
        model: str,
        api_key: str,
        encryption_key: str,
        base_url: str | None,
        is_active: bool,
    ) -> AIProviderConfig: ...

    def create_generated_content(
        self,
        *,
        product_id: int,
        template_id: int,
        platform: str,
        style: str,
        target_audience: str,
        language: str,
        provider: str,
        model: str,
        created_by: int,
    ) -> GeneratedContent: ...

    def add_content_version(
        self,
        *,
        content_id: int,
        provider: str,
        model: str,
        prompt_version: int,
        prompt_rendered: str,
        generated_text: dict[str, str],
        cost_usd: Decimal,
        latency_ms: int,
        created_by: int,
    ) -> GeneratedContentVersion: ...

    def get_content_by_id(self, content_id: int) -> GeneratedContent | None: ...

    def list_content_history(
        self, *, limit: int, offset: int, product_id: int | None = None
    ) -> list[GeneratedContent]: ...

    def count_content_history(self, *, product_id: int | None = None) -> int: ...


class AIContentRepository(AIContentRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def _template_query(self):
        return select(PromptTemplate).options(
            selectinload(PromptTemplate.prompt_variables),
        )

    def _content_query(self):
        return select(GeneratedContent).options(
            joinedload(GeneratedContent.versions),
        )

    def create_template(
        self, *, payload: PromptTemplateCreateRequest, created_by: int
    ) -> PromptTemplate:
        template = PromptTemplate(
            name=payload.name,
            category=payload.category.value,
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
            variables=[item.name for item in payload.variables],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            version=payload.version,
            status=payload.status.value,
            created_by=created_by,
        )
        self._db.add(template)
        self._db.flush()

        template.prompt_variables = [
            PromptVariable(
                template_id=template.id,
                name=item.name,
                description=item.description,
                required=item.required,
                default_value=item.default_value,
            )
            for item in payload.variables
        ]

        self._db.add(template)
        self._db.commit()
        self._db.refresh(template)
        return template

    def list_templates(
        self,
        *,
        category: PromptCategory | None,
        status: PromptTemplateStatus | None,
    ) -> list[PromptTemplate]:
        stmt = self._template_query().order_by(PromptTemplate.updated_at.desc())
        if category is not None:
            stmt = stmt.where(PromptTemplate.category == category.value)
        if status is not None:
            stmt = stmt.where(PromptTemplate.status == status.value)
        return list(self._db.scalars(stmt))

    def get_template_by_id(self, template_id: int) -> PromptTemplate | None:
        stmt = self._template_query().where(PromptTemplate.id == template_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_latest_template(
        self, *, category: PromptCategory, version: int | None = None
    ) -> PromptTemplate | None:
        stmt = self._template_query().where(
            PromptTemplate.category == category.value,
            PromptTemplate.status == PromptTemplateStatus.ACTIVE.value,
        )
        if version is not None:
            stmt = stmt.where(PromptTemplate.version == version)
        stmt = stmt.order_by(
            PromptTemplate.version.desc(), PromptTemplate.updated_at.desc()
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def update_template(
        self, *, template_id: int, payload: PromptTemplateUpdateRequest
    ) -> PromptTemplate | None:
        template = self.get_template_by_id(template_id)
        if template is None:
            return None

        data = payload.model_dump(exclude_unset=True)
        if "variables" in data:
            variables = data.pop("variables")
            template.variables = [item["name"] for item in variables]
            template.prompt_variables = [
                PromptVariable(
                    template_id=template.id,
                    name=item["name"],
                    description=item.get("description"),
                    required=bool(item.get("required", True)),
                    default_value=item.get("default_value"),
                )
                for item in variables
            ]

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
    ) -> AIProviderConfig | None:
        stmt = select(AIProviderConfig).where(
            AIProviderConfig.provider == provider,
            AIProviderConfig.model == model,
            AIProviderConfig.is_active.is_(True),
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
    ) -> AIProviderConfig:
        existing = self.get_active_provider_config(provider=provider, model=model)
        encrypted = encrypt_secret(plaintext=api_key, secret_key=encryption_key)

        if existing is None:
            config = AIProviderConfig(
                provider=provider,
                model=model,
                base_url=base_url,
                api_key_encrypted=encrypted,
                is_active=is_active,
            )
        else:
            config = existing
            config.base_url = base_url
            config.api_key_encrypted = encrypted
            config.is_active = is_active

        self._db.add(config)
        self._db.commit()
        self._db.refresh(config)
        return config

    def decrypt_provider_api_key(
        self, *, config: AIProviderConfig, encryption_key: str
    ) -> str:
        return decrypt_secret(
            ciphertext=config.api_key_encrypted, secret_key=encryption_key
        )

    def create_generated_content(
        self,
        *,
        product_id: int,
        template_id: int,
        platform: str,
        style: str,
        target_audience: str,
        language: str,
        provider: str,
        model: str,
        created_by: int,
    ) -> GeneratedContent:
        item = GeneratedContent(
            product_id=product_id,
            template_id=template_id,
            platform=platform,
            style=style,
            target_audience=target_audience,
            language=language,
            provider=provider,
            model=model,
            current_version=1,
            created_by=created_by,
        )
        self._db.add(item)
        self._db.flush()
        return item

    def add_content_version(
        self,
        *,
        content_id: int,
        provider: str,
        model: str,
        prompt_version: int,
        prompt_rendered: str,
        generated_text: dict[str, str],
        cost_usd: Decimal,
        latency_ms: int,
        created_by: int,
    ) -> GeneratedContentVersion:
        content = self.get_content_by_id(content_id)
        if content is None:
            raise ValueError("content not found")

        next_version = int(content.current_version)
        if content.versions:
            next_version = max(item.version for item in content.versions) + 1

        version = GeneratedContentVersion(
            content_id=content_id,
            version=next_version,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            prompt_rendered=prompt_rendered,
            generated_text=generated_text,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            created_by=created_by,
        )
        content.current_version = next_version
        content.provider = provider
        content.model = model

        self._db.add(version)
        self._db.add(content)
        self._db.commit()
        self._db.refresh(version)
        return version

    def get_content_by_id(self, content_id: int) -> GeneratedContent | None:
        stmt = self._content_query().where(GeneratedContent.id == content_id)
        return self._db.execute(stmt).unique().scalar_one_or_none()

    def list_content_history(
        self, *, limit: int, offset: int, product_id: int | None = None
    ) -> list[GeneratedContent]:
        stmt = self._content_query().order_by(GeneratedContent.updated_at.desc())
        if product_id is not None:
            stmt = stmt.where(GeneratedContent.product_id == product_id)
        stmt = stmt.offset(offset).limit(limit)
        return list(self._db.execute(stmt).unique().scalars())

    def count_content_history(self, *, product_id: int | None = None) -> int:
        stmt = select(func.count(GeneratedContent.id))
        if product_id is not None:
            stmt = stmt.where(GeneratedContent.product_id == product_id)
        return int(self._db.scalar(stmt) or 0)
