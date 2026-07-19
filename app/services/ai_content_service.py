from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from app.core.cache import CacheBackend
from app.core.config import Settings
from app.core.exceptions import AppException
from app.models.ai_content import GeneratedContent
from app.repositories.ai_content_repository import AIContentRepositoryProtocol
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.ai_content import (
    AIContentGenerateRequest,
    AIContentGenerateResponse,
    AIContentRead,
    AIContentRegenerateRequest,
    AIHistoryResponse,
    PromptCategory,
    PromptTemplateCreateRequest,
    PromptTemplateRead,
    PromptTemplateStatus,
    PromptTemplateUpdateRequest,
)
from app.services.ai_providers import ProviderFactory


@dataclass(frozen=True)
class _RenderedPrompt:
    prompt: str
    variables: dict[str, str]


class _GenerationRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._events: dict[int, deque[float]] = {}

    def check(self, *, user_id: int, now_ts: float) -> None:
        bucket = self._events.setdefault(user_id, deque())
        while bucket and now_ts - bucket[0] > self._window:
            bucket.popleft()
        if len(bucket) >= self._max:
            raise AppException(
                status_code=429, detail="AI generation rate limit exceeded"
            )
        bucket.append(now_ts)


class AIContentService:
    _allowed_variable_pattern = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

    def __init__(
        self,
        product_repository: ProductRepositoryProtocol,
        repository: AIContentRepositoryProtocol,
        provider_factory: ProviderFactory,
        settings: Settings,
        template_cache: CacheBackend,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._repository = repository
        self._provider_factory = provider_factory
        self._settings = settings
        self._template_cache = template_cache
        self._analytics_repository = analytics_repository
        self._rate_limiter = _GenerationRateLimiter(
            max_requests=settings.ai_generation_rate_limit_per_minute,
            window_seconds=60,
        )

    def list_templates(
        self,
        *,
        category: PromptCategory | None,
        status: PromptTemplateStatus | None,
    ) -> list[PromptTemplateRead]:
        items = self._repository.list_templates(category=category, status=status)
        return [PromptTemplateRead.model_validate(item) for item in items]

    def create_template(
        self, *, payload: PromptTemplateCreateRequest, created_by: int
    ) -> PromptTemplateRead:
        self._validate_prompt_template(payload.system_prompt, payload.user_prompt)
        item = self._repository.create_template(payload=payload, created_by=created_by)
        self._template_cache.delete(
            self._template_cache_key(payload.category, payload.version)
        )
        return PromptTemplateRead.model_validate(item)

    def update_template(
        self,
        *,
        template_id: int,
        payload: PromptTemplateUpdateRequest,
    ) -> PromptTemplateRead:
        if payload.system_prompt is not None or payload.user_prompt is not None:
            self._validate_prompt_template(
                payload.system_prompt or "ok {{product_name}}",
                payload.user_prompt or "ok {{product_name}}",
            )
        item = self._repository.update_template(
            template_id=template_id, payload=payload
        )
        if item is None:
            raise AppException(status_code=404, detail="Prompt template not found")

        self._template_cache.delete(
            self._template_cache_key(PromptCategory(item.category), item.version)
        )
        return PromptTemplateRead.model_validate(item)

    def delete_template(self, *, template_id: int) -> None:
        deleted = self._repository.delete_template(template_id=template_id)
        if not deleted:
            raise AppException(status_code=404, detail="Prompt template not found")

    async def generate(
        self,
        *,
        payload: AIContentGenerateRequest,
        created_by: int,
    ) -> AIContentGenerateResponse:
        self._rate_limiter.check(user_id=created_by, now_ts=datetime.now().timestamp())

        product = self._product_repository.get_by_id(payload.product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        template = self._resolve_template(
            category=payload.platform,
            template_id=payload.template_id,
            version=payload.template_version,
        )
        if template.status != PromptTemplateStatus.ACTIVE.value:
            raise AppException(status_code=422, detail="Prompt template is not active")

        rendered = self._render_prompt(
            template_text=f"{template.system_prompt}\n\n{template.user_prompt}",
            product_name=product.title,
            price=str(product.price),
            discount=product.discount or "",
            benefits=", ".join(payload.benefits or []),
            features=", ".join(payload.features or []),
            target_audience=payload.target_audience.value,
            platform=payload.platform.value,
            language=payload.language,
        )

        provider = self._build_provider(
            provider=payload.provider.value, model=payload.model
        )
        result = await provider.generate(
            system_prompt=template.system_prompt,
            user_prompt=rendered.prompt,
            content_types=[item.value for item in payload.content_types],
            model=payload.model,
            temperature=float(template.temperature),
            max_tokens=template.max_tokens,
        )

        checked_content = self._quality_check(
            platform=payload.platform,
            generated=result.content_by_type,
        )

        content = self._repository.create_generated_content(
            product_id=payload.product_id,
            template_id=template.id,
            platform=payload.platform.value,
            style=payload.style.value,
            target_audience=payload.target_audience.value,
            language=payload.language,
            provider=payload.provider.value,
            model=result.model,
            created_by=created_by,
        )

        version = self._repository.add_content_version(
            content_id=content.id,
            provider=payload.provider.value,
            model=result.model,
            prompt_version=template.version,
            prompt_rendered=rendered.prompt,
            generated_text=checked_content,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            created_by=created_by,
        )

        self._track_event(
            event_type="ai_content_generated",
            entity_id=content.id,
            metadata={
                "provider": payload.provider.value,
                "model": result.model,
                "platform": payload.platform.value,
                "template_version": template.version,
            },
        )

        return AIContentGenerateResponse(
            content_id=content.id,
            version_id=version.id,
            version=version.version,
            provider=version.provider,
            model=version.model,
            prompt_version=version.prompt_version,
            generated_text=version.generated_text,
            cost_usd=version.cost_usd,
            latency_ms=version.latency_ms,
            created_at=version.created_at,
        )

    async def regenerate(
        self,
        *,
        payload: AIContentRegenerateRequest,
        created_by: int,
    ) -> AIContentGenerateResponse:
        self._rate_limiter.check(user_id=created_by, now_ts=datetime.now().timestamp())

        content = self._repository.get_content_by_id(payload.content_id)
        if content is None:
            raise AppException(status_code=404, detail="Content history not found")

        latest = self._latest_version(content)
        template = self._repository.get_template_by_id(content.template_id)
        if template is None:
            raise AppException(status_code=404, detail="Prompt template not found")

        provider_name = (
            payload.provider.value if payload.provider is not None else latest.provider
        )
        model_name = payload.model or latest.model
        provider = self._build_provider(provider=provider_name, model=model_name)

        content_types = list(latest.generated_text.keys())
        result = await provider.generate(
            system_prompt=template.system_prompt,
            user_prompt=latest.prompt_rendered,
            content_types=content_types,
            model=model_name,
            temperature=float(template.temperature),
            max_tokens=template.max_tokens,
        )

        checked = self._quality_check(
            platform=PromptCategory(content.platform),
            generated=result.content_by_type,
            previous=latest.generated_text,
        )

        version = self._repository.add_content_version(
            content_id=content.id,
            provider=provider_name,
            model=result.model,
            prompt_version=template.version,
            prompt_rendered=latest.prompt_rendered,
            generated_text=checked,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            created_by=created_by,
        )

        self._track_event(
            event_type="ai_content_regenerated",
            entity_id=content.id,
            metadata={
                "provider": provider_name,
                "model": result.model,
                "platform": content.platform,
                "version": version.version,
            },
        )

        return AIContentGenerateResponse(
            content_id=content.id,
            version_id=version.id,
            version=version.version,
            provider=version.provider,
            model=version.model,
            prompt_version=version.prompt_version,
            generated_text=version.generated_text,
            cost_usd=version.cost_usd,
            latency_ms=version.latency_ms,
            created_at=version.created_at,
        )

    def history(
        self,
        *,
        limit: int,
        offset: int,
        product_id: int | None,
    ) -> AIHistoryResponse:
        items = self._repository.list_content_history(
            limit=limit,
            offset=offset,
            product_id=product_id,
        )
        total = self._repository.count_content_history(product_id=product_id)
        return AIHistoryResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[self._to_read_model(item) for item in items],
        )

    def _resolve_template(
        self, *, category: PromptCategory, template_id: int | None, version: int | None
    ):
        if template_id is not None:
            template = self._repository.get_template_by_id(template_id)
            if template is None:
                raise AppException(status_code=404, detail="Prompt template not found")
            return template

        cache_key = self._template_cache_key(category, version)
        cached_template_id = self._template_cache.get(cache_key)
        if cached_template_id is not None:
            template = self._repository.get_template_by_id(int(cached_template_id))
            if template is not None:
                return template

        template = self._repository.get_latest_template(
            category=category, version=version
        )
        if template is None:
            raise AppException(
                status_code=404, detail="No active prompt template found"
            )

        self._template_cache.set(
            cache_key,
            str(template.id),
            ttl_seconds=self._settings.ai_template_cache_ttl_seconds,
        )
        return template

    def _build_provider(self, *, provider: str, model: str):
        config = self._repository.get_active_provider_config(
            provider=provider, model=model
        )

        api_key: str | None = None
        base_url: str | None = None
        if config is not None:
            api_key = self._repository.decrypt_provider_api_key(
                config=config,
                encryption_key=self._settings.ai_provider_encryption_key,
            )
            base_url = config.base_url

        if api_key is None:
            env_map = {
                "openai": self._settings.openai_api_key,
                "gemini": self._settings.gemini_api_key,
                "claude": self._settings.claude_api_key,
                "deepseek": self._settings.deepseek_api_key,
                "openrouter": self._settings.openrouter_api_key,
            }
            api_key = env_map.get(provider)

        if not api_key:
            raise AppException(
                status_code=503,
                detail=f"Provider credentials not configured: {provider}",
            )

        return self._provider_factory.get_provider(
            provider_name=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

    def _render_prompt(
        self, *, template_text: str, **variables: str
    ) -> _RenderedPrompt:
        placeholders = set(self._allowed_variable_pattern.findall(template_text))
        missing = [name for name in placeholders if not variables.get(name)]
        if missing:
            raise AppException(
                status_code=422,
                detail=f"Missing prompt variables: {', '.join(sorted(missing))}",
            )

        rendered = template_text
        for name, value in variables.items():
            rendered = rendered.replace(f"{{{{{name}}}}}", value or "")
        return _RenderedPrompt(prompt=rendered.strip(), variables=variables)

    def _validate_prompt_template(self, system_prompt: str, user_prompt: str) -> None:
        merged = f"{system_prompt}\n{user_prompt}".lower()
        forbidden = ["ignore previous instructions", "system override", "jailbreak"]
        for item in forbidden:
            if item in merged:
                raise AppException(
                    status_code=422,
                    detail="Prompt template contains forbidden instruction patterns",
                )

    def _quality_check(
        self,
        *,
        platform: PromptCategory,
        generated: dict[str, str],
        previous: dict[str, str] | None = None,
    ) -> dict[str, str]:
        checked: dict[str, str] = {}
        min_length = 20
        max_length_map = {
            PromptCategory.FACEBOOK: 2200,
            PromptCategory.TIKTOK: 400,
            PromptCategory.INSTAGRAM: 2200,
            PromptCategory.YOUTUBE_SHORTS: 5000,
            PromptCategory.SHOPEE_LIVE: 800,
            PromptCategory.GENERAL_AFFILIATE: 2200,
        }
        banned_words = {
            item.strip().lower()
            for item in self._settings.ai_banned_words.split(",")
            if item.strip()
        }

        for key, value in generated.items():
            text = value.strip()
            if len(text) < min_length:
                raise AppException(
                    status_code=422, detail=f"Generated content too short: {key}"
                )

            if len(text) > max_length_map[platform]:
                text = text[: max_length_map[platform]].rstrip()

            lowered = text.lower()
            if any(bad in lowered for bad in banned_words):
                raise AppException(
                    status_code=422,
                    detail=f"Generated content contains banned words: {key}",
                )

            if (
                previous is not None
                and previous.get(key, "").strip().lower() == lowered
            ):
                raise AppException(
                    status_code=422, detail=f"Regenerated content is duplicated: {key}"
                )

            if "hashtag" in key and "#" in text:
                tags = [item for item in text.split() if item.startswith("#")]
                tags = list(dict.fromkeys(tags))[:8]
                text = " ".join(tags)
            elif "hashtag" in key and "#" not in text:
                text = "#affiliate #product #deal"

            if "caption" in key and not any(
                ch in text for ch in ["😀", "🔥", "✨", "✅", "💡"]
            ):
                text = f"🔥 {text}"

            checked[key] = text

        values = [item.lower() for item in checked.values()]
        if len(values) != len(set(values)):
            raise AppException(
                status_code=422,
                detail="Generated content is duplicated across content types",
            )

        return checked

    def _latest_version(self, content: GeneratedContent):
        if not content.versions:
            raise AppException(
                status_code=404, detail="Generated content version not found"
            )
        return sorted(content.versions, key=lambda item: item.version, reverse=True)[0]

    def _to_read_model(self, item: GeneratedContent) -> AIContentRead:
        latest = self._latest_version(item)
        payload = {
            "id": item.id,
            "product_id": item.product_id,
            "template_id": item.template_id,
            "platform": item.platform,
            "style": item.style,
            "target_audience": item.target_audience,
            "language": item.language,
            "provider": item.provider,
            "model": item.model,
            "current_version": item.current_version,
            "created_by": item.created_by,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "latest_generated_text": latest.generated_text,
        }
        return AIContentRead.model_validate(payload)

    def _template_cache_key(self, category: PromptCategory, version: int | None) -> str:
        suffix = str(version) if version is not None else "latest"
        return f"ai:template:{category.value}:{suffix}"

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
            entity_type="generated_content",
            entity_id=entity_id,
            metadata=metadata,
        )
