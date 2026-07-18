from datetime import UTC, datetime, timedelta
import re
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.product import (
    Product,
    ProductCategory,
    ProductImage,
    ProductPriceHistory,
    ProductVersionHistory,
)
from app.schemas.product import ProductPayload, ProductUpdateRequest


class ProductRepositoryProtocol(Protocol):
    def get_by_id(self, product_id: int) -> Product | None: ...

    def get_by_normalized_url(self, normalized_url: str) -> Product | None: ...

    def get_valid_by_normalized_url(
        self, normalized_url: str, now: datetime
    ) -> Product | None: ...

    def get_by_fingerprint(self, fingerprint: str) -> Product | None: ...

    def count_products(
        self, *, search: str | None = None, marketplace: str | None = None
    ) -> int: ...

    def list_products(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        marketplace: str | None = None,
    ) -> list[Product]: ...

    def delete_product(self, product_id: int) -> bool: ...

    def update_product(
        self, *, product_id: int, payload: ProductUpdateRequest
    ) -> Product | None: ...

    def upsert_from_provider(
        self,
        *,
        source_url: str,
        normalized_url: str,
        marketplace: str,
        external_product_id: str | None,
        fingerprint: str,
        payload: ProductPayload,
        now: datetime,
        ttl_minutes: int,
        change_reason: str,
    ) -> Product: ...

    def get_valid_by_source_url(
        self, source_url: str, now: datetime
    ) -> Product | None: ...

    def upsert_cached(
        self,
        *,
        source_url: str,
        payload: ProductPayload,
        now: datetime,
        ttl_minutes: int,
    ) -> Product: ...


class ProductRepository(ProductRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def _aggregate_query(self):
        return select(Product).options(
            joinedload(Product.category_ref),
            selectinload(Product.image_items),
            selectinload(Product.price_history_items),
            selectinload(Product.version_history_items),
        )

    def _hydrate_compatibility_fields(self, product: Product) -> Product:
        if product.image_items:
            product.images = [
                image.image_url
                for image in sorted(product.image_items, key=lambda x: x.sort_order)
            ]
        if product.category_ref is not None:
            product.category = product.category_ref.name
        return product

    def _slugify_category(self, value: str) -> str:
        return (
            re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
            or "uncategorized"
        )

    def _resolve_category(self, category_name: str | None) -> ProductCategory | None:
        if not category_name or not category_name.strip():
            return None
        normalized = category_name.strip()
        stmt = select(ProductCategory).where(ProductCategory.name == normalized)
        category = self._db.execute(stmt).scalar_one_or_none()
        if category is not None:
            return category

        category = ProductCategory(
            name=normalized, slug=self._slugify_category(normalized)
        )
        self._db.add(category)
        self._db.flush()
        return category

    def _append_price_history(
        self, *, product: Product, payload: ProductPayload, now: datetime
    ) -> None:
        self._db.add(
            ProductPriceHistory(
                product_id=product.id,
                price=payload.price,
                original_price=payload.original_price,
                discount=payload.discount,
                captured_at=now,
            )
        )

    def _append_version_history(
        self, *, product: Product, fingerprint: str, change_reason: str
    ) -> None:
        self._db.add(
            ProductVersionHistory(
                product_id=product.id,
                version=product.aggregate_version,
                fingerprint=fingerprint,
                title=product.title,
                price=product.price,
                original_price=product.original_price,
                discount=product.discount,
                rating=product.rating,
                sold_count=product.sold_count,
                images=product.images,
                shop_name=product.shop_name,
                category=product.category,
                affiliate_url=product.affiliate_url,
                change_reason=change_reason,
            )
        )

    def get_by_id(self, product_id: int) -> Product | None:
        stmt = self._aggregate_query().where(Product.id == product_id)
        product = self._db.execute(stmt).scalar_one_or_none()
        if product is None:
            return None
        return self._hydrate_compatibility_fields(product)

    def get_by_normalized_url(self, normalized_url: str) -> Product | None:
        stmt = self._aggregate_query().where(Product.normalized_url == normalized_url)
        product = self._db.execute(stmt).scalar_one_or_none()
        if product is None:
            return None
        return self._hydrate_compatibility_fields(product)

    def get_valid_by_normalized_url(
        self, normalized_url: str, now: datetime
    ) -> Product | None:
        stmt = self._aggregate_query().where(
            Product.normalized_url == normalized_url,
            Product.expires_at > now,
        )
        product = self._db.execute(stmt).scalar_one_or_none()
        if product is None:
            return None
        return self._hydrate_compatibility_fields(product)

    def get_by_fingerprint(self, fingerprint: str) -> Product | None:
        stmt = self._aggregate_query().where(Product.fingerprint == fingerprint)
        product = self._db.execute(stmt).scalar_one_or_none()
        if product is None:
            return None
        return self._hydrate_compatibility_fields(product)

    def get_valid_by_source_url(self, source_url: str, now: datetime) -> Product | None:
        stmt = self._aggregate_query().where(
            Product.source_url == source_url, Product.expires_at > now
        )
        product = self._db.execute(stmt).scalar_one_or_none()
        if product is None:
            return None
        return self._hydrate_compatibility_fields(product)

    def count_products(
        self,
        *,
        search: str | None = None,
        marketplace: str | None = None,
    ) -> int:
        stmt = select(func.count(Product.id))
        if marketplace:
            stmt = stmt.where(Product.marketplace == marketplace)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(
                Product.title.ilike(like)
                | Product.shop_name.ilike(like)
                | Product.category.ilike(like)
            )
        return int(self._db.scalar(stmt) or 0)

    def list_products(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        marketplace: str | None = None,
    ) -> list[Product]:
        stmt = self._aggregate_query().order_by(Product.updated_at.desc())
        if marketplace:
            stmt = stmt.where(Product.marketplace == marketplace)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(
                Product.title.ilike(like)
                | Product.shop_name.ilike(like)
                | Product.category.ilike(like)
            )
        stmt = stmt.offset(offset).limit(limit)
        rows = list(self._db.execute(stmt).scalars())
        return [self._hydrate_compatibility_fields(item) for item in rows]

    def delete_product(self, product_id: int) -> bool:
        product = self._db.get(Product, product_id)
        if product is None:
            return False
        self._db.delete(product)
        self._db.commit()
        return True

    def update_product(
        self, *, product_id: int, payload: ProductUpdateRequest
    ) -> Product | None:
        product = self._db.get(Product, product_id)
        if product is None:
            return None

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key == "images" and value is not None:
                images = [str(item) for item in value]
                product.images = images
                product.image_items = [
                    ProductImage(image_url=image_url, sort_order=index)
                    for index, image_url in enumerate(images)
                ]
                continue
            if key == "category":
                category_name = str(value) if value is not None else None
                product.category = category_name
                product.category_ref = self._resolve_category(category_name)
                continue
            if key == "affiliate_url" and value is not None:
                product.affiliate_url = str(value)
                continue
            setattr(product, key, value)

        product.aggregate_version = int(product.aggregate_version) + 1
        self._append_version_history(
            product=product,
            fingerprint=product.fingerprint,
            change_reason="manual_update",
        )
        self._db.add(product)
        self._db.commit()
        self._db.refresh(product)
        return self._hydrate_compatibility_fields(product)

    def upsert_from_provider(
        self,
        *,
        source_url: str,
        normalized_url: str,
        marketplace: str,
        external_product_id: str | None,
        fingerprint: str,
        payload: ProductPayload,
        now: datetime,
        ttl_minutes: int,
        change_reason: str,
    ) -> Product:
        product = self._db.execute(
            self._aggregate_query().where(
                (Product.fingerprint == fingerprint)
                | (Product.normalized_url == normalized_url)
            )
        ).scalar_one_or_none()

        expires_at = now + timedelta(minutes=ttl_minutes)
        category_ref = self._resolve_category(payload.category)
        image_urls = [str(item) for item in payload.images]

        if product is None:
            product = Product(
                source_url=source_url,
                normalized_url=normalized_url,
                marketplace=marketplace,
                external_product_id=external_product_id,
                fingerprint=fingerprint,
                aggregate_version=1,
                expires_at=expires_at,
                title=payload.title,
                price=payload.price,
                original_price=payload.original_price,
                discount=payload.discount,
                rating=payload.rating,
                sold_count=payload.sold_count,
                images=image_urls,
                shop_name=payload.shop_name,
                category=payload.category,
                category_ref=category_ref,
                affiliate_url=payload.affiliate_url,
            )
            self._db.add(product)
            self._db.flush()
        else:
            product.source_url = source_url
            product.normalized_url = normalized_url
            product.marketplace = marketplace
            product.external_product_id = external_product_id
            product.fingerprint = fingerprint
            product.expires_at = expires_at
            product.title = payload.title
            product.price = payload.price
            product.original_price = payload.original_price
            product.discount = payload.discount
            product.rating = payload.rating
            product.sold_count = payload.sold_count
            product.images = image_urls
            product.shop_name = payload.shop_name
            product.category = payload.category
            product.category_ref = category_ref
            product.affiliate_url = payload.affiliate_url
            product.aggregate_version = int(product.aggregate_version) + 1

        product.image_items = [
            ProductImage(image_url=image_url, sort_order=index)
            for index, image_url in enumerate(image_urls)
        ]

        self._append_price_history(product=product, payload=payload, now=now)
        self._append_version_history(
            product=product,
            fingerprint=fingerprint,
            change_reason=change_reason,
        )

        self._db.add(product)
        self._db.commit()
        self._db.refresh(product)
        return self._hydrate_compatibility_fields(product)

    def upsert_cached(
        self,
        *,
        source_url: str,
        payload: ProductPayload,
        now: datetime,
        ttl_minutes: int,
    ) -> Product:
        normalized_url = payload.normalized_url or source_url
        fingerprint = f"legacy-{normalized_url}"
        return self.upsert_from_provider(
            source_url=source_url,
            normalized_url=normalized_url,
            marketplace=payload.marketplace or "shopee",
            external_product_id=payload.external_product_id,
            fingerprint=fingerprint,
            payload=payload,
            now=now,
            ttl_minutes=ttl_minutes,
            change_reason="legacy_upsert",
        )


def utc_now() -> datetime:
    return datetime.now(UTC)
