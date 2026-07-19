from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ImageTemplate(Base):
    __tablename__ = "image_templates"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_image_templates_name_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    image_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    canvas_width: Mapped[int] = mapped_column(Integer, nullable=False)
    canvas_height: Mapped[int] = mapped_column(Integer, nullable=False)
    safe_area: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    background: Mapped[dict[str, str | int]] = mapped_column(JSON, nullable=False)
    layers: Mapped[list[dict[str, str | int | float | bool]]] = mapped_column(
        JSON, nullable=False
    )
    fonts: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    colors: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    logo_position: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    watermark: Mapped[dict[str, str | int | bool]] = mapped_column(JSON, nullable=False)
    overlay: Mapped[dict[str, str | int | float | bool]] = mapped_column(
        JSON, nullable=False
    )
    dynamic_variables: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
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


class ImageProviderConfig(Base):
    __tablename__ = "image_provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ImageAsset(Base):
    __tablename__ = "image_assets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    caption_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("generated_contents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("image_templates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    image_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=0
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

    versions: Mapped[list["GeneratedImageVersion"]] = relationship(
        "GeneratedImageVersion",
        back_populates="generated_image",
        cascade="all, delete-orphan",
        order_by="GeneratedImageVersion.version.desc()",
    )


class GeneratedImageVersion(Base):
    __tablename__ = "generated_image_versions"
    __table_args__ = (
        UniqueConstraint(
            "generated_image_id",
            "version",
            name="uq_generated_image_versions_image_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    generated_image_id: Mapped[int] = mapped_column(
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_variables: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    output_format: Mapped[str] = mapped_column(String(16), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    image_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    preview_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    thumbnail_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    generated_image: Mapped[GeneratedImage] = relationship(
        "GeneratedImage", back_populates="versions"
    )


class ImageHistory(Base):
    __tablename__ = "image_histories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    generated_image_id: Mapped[int] = mapped_column(
        ForeignKey("generated_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_image_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("generated_image_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_metadata: Mapped[dict[str, str | int | float | bool | None]] = mapped_column(
        JSON, nullable=False
    )
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
