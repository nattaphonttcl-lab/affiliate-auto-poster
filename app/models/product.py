from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_url: Mapped[str] = mapped_column(
        String(2048), unique=True, nullable=False, index=True
    )
    normalized_url: Mapped[str] = mapped_column(
        String(2048), unique=True, nullable=False, index=True
    )
    marketplace: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_product_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    aggregate_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    discount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    sold_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    images: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affiliate_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category_ref: Mapped["ProductCategory | None"] = relationship(
        "ProductCategory",
        lazy="joined",
    )
    image_items: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    price_history_items: Mapped[list["ProductPriceHistory"]] = relationship(
        "ProductPriceHistory",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductPriceHistory.captured_at.desc()",
    )
    version_history_items: Mapped[list["ProductVersionHistory"]] = relationship(
        "ProductVersionHistory",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVersionHistory.version.desc()",
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped[Product] = relationship("Product", back_populates="image_items")


class ProductPriceHistory(Base):
    __tablename__ = "product_price_histories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    discount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    product: Mapped[Product] = relationship(
        "Product", back_populates="price_history_items"
    )


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProductVersionHistory(Base):
    __tablename__ = "product_version_histories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    discount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    sold_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    images: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affiliate_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    product: Mapped[Product] = relationship(
        "Product",
        back_populates="version_history_items",
    )
