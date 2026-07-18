from __future__ import annotations

from datetime import UTC, datetime

from app.core.cache import CacheBackend
from app.core.exceptions import AppException
from app.models.product import Product
from app.repositories.analytics_repository import AnalyticsRepositoryProtocol
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.product import ProductListResponse, ProductRead, ProductUpdateRequest
from app.services.marketplace_provider import MarketplaceProviderRegistry
from app.services.product_fingerprint import build_product_fingerprint
from app.services.refresh_queue import ProductRefreshQueue


class ProductService:
    def __init__(
        self,
        repository: ProductRepositoryProtocol,
        provider_registry: MarketplaceProviderRegistry,
        cache: CacheBackend,
        refresh_queue: ProductRefreshQueue,
        *,
        cache_ttl_minutes: int,
        analytics_repository: AnalyticsRepositoryProtocol | None = None,
    ) -> None:
        self._repository = repository
        self._provider_registry = provider_registry
        self._cache = cache
        self._refresh_queue = refresh_queue
        self._cache_ttl_minutes = cache_ttl_minutes
        self._analytics_repository = analytics_repository

    def import_product(self, *, source_url: str) -> Product:
        provider = self._provider_registry.resolve(source_url)
        normalized_url = provider.normalize_url(source_url)
        now = datetime.now(UTC)

        cached_id = self._cache.get(self._cache_key(normalized_url))
        if cached_id is not None:
            cached = self._repository.get_by_id(int(cached_id))
            if cached is not None and self._is_not_expired(cached.expires_at, now):
                self._track_event(
                    event_type="product_cache_hit",
                    entity_id=cached.id,
                    metadata={
                        "normalized_url": normalized_url,
                        "marketplace": cached.marketplace,
                    },
                )
                return cached

        valid = self._repository.get_valid_by_normalized_url(normalized_url, now)
        if valid is not None:
            self._cache.set(
                self._cache_key(normalized_url),
                str(valid.id),
                ttl_seconds=self._cache_ttl_minutes * 60,
            )
            self._track_event(
                event_type="product_cache_hit",
                entity_id=valid.id,
                metadata={
                    "normalized_url": normalized_url,
                    "marketplace": valid.marketplace,
                },
            )
            return valid

        payload = provider.fetch_product(normalized_url)
        fingerprint = build_product_fingerprint(
            marketplace=provider.marketplace,
            normalized_url=normalized_url,
            external_product_id=payload.external_product_id,
        )

        saved = self._repository.upsert_from_provider(
            source_url=source_url,
            normalized_url=normalized_url,
            marketplace=provider.marketplace,
            external_product_id=payload.external_product_id,
            fingerprint=fingerprint,
            payload=payload,
            now=now,
            ttl_minutes=self._cache_ttl_minutes,
            change_reason="import",
        )
        self._cache.set(
            self._cache_key(normalized_url),
            str(saved.id),
            ttl_seconds=self._cache_ttl_minutes * 60,
        )

        self._track_event(
            event_type="product_imported",
            entity_id=saved.id,
            metadata={
                "normalized_url": normalized_url,
                "marketplace": provider.marketplace,
            },
        )
        return saved

    def refresh_product(
        self, *, product_id: int, requested_by_user_id: int, background: bool = False
    ) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        if background:
            self._refresh_queue.enqueue_refresh(
                product_id=product_id,
                requested_by_user_id=requested_by_user_id,
            )
            self._track_event(
                event_type="product_refresh_queued",
                entity_id=product_id,
                metadata={"marketplace": product.marketplace},
            )
            return product

        provider = self._provider_registry.get_by_marketplace(product.marketplace)
        normalized_url = provider.normalize_url(product.source_url)
        payload = provider.fetch_product(normalized_url)
        fingerprint = build_product_fingerprint(
            marketplace=provider.marketplace,
            normalized_url=normalized_url,
            external_product_id=payload.external_product_id,
        )

        refreshed = self._repository.upsert_from_provider(
            source_url=product.source_url,
            normalized_url=normalized_url,
            marketplace=provider.marketplace,
            external_product_id=payload.external_product_id,
            fingerprint=fingerprint,
            payload=payload,
            now=datetime.now(UTC),
            ttl_minutes=self._cache_ttl_minutes,
            change_reason="refresh",
        )
        self._cache.set(
            self._cache_key(normalized_url),
            str(refreshed.id),
            ttl_seconds=self._cache_ttl_minutes * 60,
        )

        self._track_event(
            event_type="product_refreshed",
            entity_id=refreshed.id,
            metadata={"marketplace": refreshed.marketplace},
        )
        return refreshed

    def update_product(
        self, *, product_id: int, payload: ProductUpdateRequest
    ) -> Product:
        updated = self._repository.update_product(
            product_id=product_id, payload=payload
        )
        if updated is None:
            raise AppException(status_code=404, detail="Product not found")

        self._cache.set(
            self._cache_key(updated.normalized_url),
            str(updated.id),
            ttl_seconds=self._cache_ttl_minutes * 60,
        )
        self._track_event(
            event_type="product_updated",
            entity_id=updated.id,
            metadata={"marketplace": updated.marketplace},
        )
        return updated

    def delete_product(self, *, product_id: int) -> None:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")

        deleted = self._repository.delete_product(product_id)
        if not deleted:
            raise AppException(status_code=404, detail="Product not found")

        self._cache.delete(self._cache_key(product.normalized_url))
        self._track_event(
            event_type="product_deleted",
            entity_id=product_id,
            metadata={"marketplace": product.marketplace},
        )

    def get_product(self, *, product_id: int) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise AppException(status_code=404, detail="Product not found")
        return product

    def list_products(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        marketplace: str | None = None,
    ) -> ProductListResponse:
        total = self._repository.count_products(search=search, marketplace=marketplace)
        items = self._repository.list_products(
            limit=limit,
            offset=offset,
            search=search,
            marketplace=marketplace,
        )
        return ProductListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[ProductRead.model_validate(item) for item in items],
        )

    def search_products(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
        marketplace: str | None = None,
    ) -> ProductListResponse:
        return self.list_products(
            limit=limit,
            offset=offset,
            search=query,
            marketplace=marketplace,
        )

    def _cache_key(self, normalized_url: str) -> str:
        return f"product:url:{normalized_url.lower()}"

    def _is_not_expired(self, expires_at: datetime, now: datetime) -> bool:
        if expires_at.tzinfo is None:
            return expires_at > now.replace(tzinfo=None)
        return expires_at > now

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
            entity_type="product",
            entity_id=entity_id,
            metadata=metadata,
        )
