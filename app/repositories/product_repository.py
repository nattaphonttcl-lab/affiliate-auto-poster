from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductPayload


class ProductRepositoryProtocol(Protocol):
    def get_by_id(self, product_id: int) -> Product | None: ...

    def get_valid_by_source_url(
        self, source_url: str, now: datetime
    ) -> Product | None: ...

    def upsert_cached(
        self,
        *,
        source_url: str,
        payload: ProductPayload,
        now: datetime,
        ttl_minutes: int
    ) -> Product: ...


class ProductRepository(ProductRepositoryProtocol):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, product_id: int) -> Product | None:
        return self._db.get(Product, product_id)

    def get_valid_by_source_url(self, source_url: str, now: datetime) -> Product | None:
        stmt = select(Product).where(
            Product.source_url == source_url, Product.expires_at > now
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def upsert_cached(
        self,
        *,
        source_url: str,
        payload: ProductPayload,
        now: datetime,
        ttl_minutes: int
    ) -> Product:
        product = self._db.execute(
            select(Product).where(Product.source_url == source_url)
        ).scalar_one_or_none()
        expires_at = now + timedelta(minutes=ttl_minutes)

        if product is None:
            product = Product(
                source_url=source_url,
                expires_at=expires_at,
                title=payload.title,
                price=payload.price,
                original_price=payload.original_price,
                discount=payload.discount,
                rating=payload.rating,
                sold_count=payload.sold_count,
                images=payload.images,
                shop_name=payload.shop_name,
                category=payload.category,
                affiliate_url=payload.affiliate_url,
            )
        else:
            product.expires_at = expires_at
            product.title = payload.title
            product.price = payload.price
            product.original_price = payload.original_price
            product.discount = payload.discount
            product.rating = payload.rating
            product.sold_count = payload.sold_count
            product.images = payload.images
            product.shop_name = payload.shop_name
            product.category = payload.category
            product.affiliate_url = payload.affiliate_url

        self._db.add(product)
        self._db.commit()
        self._db.refresh(product)
        return product


def utc_now() -> datetime:
    return datetime.now(UTC)
