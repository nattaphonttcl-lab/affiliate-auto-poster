"""product aggregate normalization

Revision ID: 20260719_0010
Revises: 20260719_0009
Create Date: 2026-07-19 10:00:00
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0010"
down_revision = "20260719_0009"
branch_labels = None
depends_on = None


product_categories_table = sa.table(
    "product_categories",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
)


products_table = sa.table(
    "products",
    sa.column("id", sa.Integer),
    sa.column("source_url", sa.String),
    sa.column("normalized_url", sa.String),
    sa.column("marketplace", sa.String),
    sa.column("title", sa.String),
    sa.column("external_product_id", sa.String),
    sa.column("fingerprint", sa.String),
    sa.column("aggregate_version", sa.Integer),
    sa.column("category", sa.String),
    sa.column("category_id", sa.Integer),
    sa.column("images", sa.JSON),
    sa.column("price", sa.Numeric),
    sa.column("original_price", sa.Numeric),
    sa.column("discount", sa.String),
    sa.column("rating", sa.Float),
    sa.column("sold_count", sa.Integer),
    sa.column("shop_name", sa.String),
    sa.column("affiliate_url", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


product_version_histories_table = sa.table(
    "product_version_histories",
    sa.column("product_id", sa.Integer),
    sa.column("version", sa.Integer),
    sa.column("fingerprint", sa.String),
    sa.column("title", sa.String),
    sa.column("price", sa.Numeric),
    sa.column("original_price", sa.Numeric),
    sa.column("discount", sa.String),
    sa.column("rating", sa.Float),
    sa.column("sold_count", sa.Integer),
    sa.column("images", sa.JSON),
    sa.column("shop_name", sa.String),
    sa.column("category", sa.String),
    sa.column("affiliate_url", sa.String),
    sa.column("change_reason", sa.String),
)


product_images_table = sa.table(
    "product_images",
    sa.column("product_id", sa.Integer),
    sa.column("image_url", sa.String),
    sa.column("sort_order", sa.Integer),
)


product_price_histories_table = sa.table(
    "product_price_histories",
    sa.column("product_id", sa.Integer),
    sa.column("price", sa.Numeric),
    sa.column("original_price", sa.Numeric),
    sa.column("discount", sa.String),
    sa.column("captured_at", sa.DateTime(timezone=True)),
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "uncategorized"


def _fingerprint(
    *, marketplace: str, external_product_id: str | None, normalized_url: str
) -> str:
    basis = f"{marketplace.strip().lower()}|{(external_product_id or '').strip()}|{normalized_url.strip().lower()}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _fk_exists(table_name: str, fk_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name)
    )


def upgrade() -> None:
    if not _column_exists("products", "normalized_url"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.add_column(
                sa.Column("normalized_url", sa.String(length=2048), nullable=True)
            )

    if not _column_exists("products", "marketplace"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "marketplace",
                    sa.String(length=32),
                    nullable=False,
                    server_default="shopee",
                )
            )

    if not _column_exists("products", "external_product_id"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.add_column(
                sa.Column("external_product_id", sa.String(length=128), nullable=True)
            )

    if not _column_exists("products", "fingerprint"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.add_column(
                sa.Column("fingerprint", sa.String(length=64), nullable=True)
            )

    if not _column_exists("products", "aggregate_version"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "aggregate_version",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )

    if not _column_exists("products", "category_id"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))

    if not _index_exists("products", "ix_products_normalized_url"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_index(
                "ix_products_normalized_url", ["normalized_url"], unique=True
            )

    if not _index_exists("products", "ix_products_marketplace"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_index(
                "ix_products_marketplace", ["marketplace"], unique=False
            )

    if not _index_exists("products", "ix_products_external_product_id"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_index(
                "ix_products_external_product_id", ["external_product_id"], unique=False
            )

    if not _index_exists("products", "ix_products_fingerprint"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_index(
                "ix_products_fingerprint", ["fingerprint"], unique=True
            )

    if not _index_exists("products", "ix_products_aggregate_version"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_index(
                "ix_products_aggregate_version", ["aggregate_version"], unique=False
            )

    if not _index_exists("products", "ix_products_category_id"):
        with op.batch_alter_table("products") as batch_op:
            batch_op.create_index(
                "ix_products_category_id", ["category_id"], unique=False
            )

    if not _index_exists("products", "ix_products_marketplace_external_product_id"):
        op.create_index(
            "ix_products_marketplace_external_product_id",
            "products",
            ["marketplace", "external_product_id"],
            unique=True,
        )

    if not _table_exists("product_categories"):
        op.create_table(
            "product_categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False, unique=True),
            sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _index_exists("product_categories", "ix_product_categories_id"):
        op.create_index(
            "ix_product_categories_id", "product_categories", ["id"], unique=False
        )
    if not _index_exists("product_categories", "ix_product_categories_slug"):
        op.create_index(
            "ix_product_categories_slug", "product_categories", ["slug"], unique=True
        )

    if not _table_exists("product_images"):
        op.create_table(
            "product_images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("image_url", sa.String(length=2048), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _index_exists("product_images", "ix_product_images_id"):
        op.create_index("ix_product_images_id", "product_images", ["id"], unique=False)
    if not _index_exists("product_images", "ix_product_images_product_id"):
        op.create_index(
            "ix_product_images_product_id",
            "product_images",
            ["product_id"],
            unique=False,
        )
    if not _index_exists("product_images", "ix_product_images_product_id_sort_order"):
        op.create_index(
            "ix_product_images_product_id_sort_order",
            "product_images",
            ["product_id", "sort_order"],
            unique=False,
        )

    if not _table_exists("product_price_histories"):
        op.create_table(
            "product_price_histories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column(
                "original_price", sa.Numeric(precision=12, scale=2), nullable=True
            ),
            sa.Column("discount", sa.String(length=64), nullable=True),
            sa.Column(
                "captured_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _index_exists("product_price_histories", "ix_product_price_histories_id"):
        op.create_index(
            "ix_product_price_histories_id",
            "product_price_histories",
            ["id"],
            unique=False,
        )
    if not _index_exists(
        "product_price_histories", "ix_product_price_histories_product_id"
    ):
        op.create_index(
            "ix_product_price_histories_product_id",
            "product_price_histories",
            ["product_id"],
            unique=False,
        )
    if not _index_exists(
        "product_price_histories", "ix_product_price_histories_product_id_captured_at"
    ):
        op.create_index(
            "ix_product_price_histories_product_id_captured_at",
            "product_price_histories",
            ["product_id", "captured_at"],
            unique=False,
        )

    if not _table_exists("product_version_histories"):
        op.create_table(
            "product_version_histories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("fingerprint", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column(
                "original_price", sa.Numeric(precision=12, scale=2), nullable=True
            ),
            sa.Column("discount", sa.String(length=64), nullable=True),
            sa.Column("rating", sa.Float(), nullable=True),
            sa.Column("sold_count", sa.Integer(), nullable=True),
            sa.Column("images", sa.JSON(), nullable=False),
            sa.Column("shop_name", sa.String(length=255), nullable=True),
            sa.Column("category", sa.String(length=255), nullable=True),
            sa.Column("affiliate_url", sa.String(length=2048), nullable=False),
            sa.Column("change_reason", sa.String(length=64), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _index_exists(
        "product_version_histories", "ix_product_version_histories_id"
    ):
        op.create_index(
            "ix_product_version_histories_id",
            "product_version_histories",
            ["id"],
            unique=False,
        )
    if not _index_exists(
        "product_version_histories", "ix_product_version_histories_product_id"
    ):
        op.create_index(
            "ix_product_version_histories_product_id",
            "product_version_histories",
            ["product_id"],
            unique=False,
        )
    if not _index_exists(
        "product_version_histories", "ix_product_version_histories_product_id_version"
    ):
        op.create_index(
            "ix_product_version_histories_product_id_version",
            "product_version_histories",
            ["product_id", "version"],
            unique=False,
        )

    op.execute(
        "UPDATE products SET normalized_url = source_url WHERE normalized_url IS NULL"
    )

    connection = op.get_bind()

    products = list(
        connection.execute(
            sa.select(
                products_table.c.id,
                products_table.c.source_url,
                products_table.c.normalized_url,
                products_table.c.title,
                products_table.c.category,
                products_table.c.images,
                products_table.c.price,
                products_table.c.original_price,
                products_table.c.discount,
                products_table.c.rating,
                products_table.c.sold_count,
                products_table.c.shop_name,
                products_table.c.affiliate_url,
                products_table.c.created_at,
            )
        )
    )

    category_name_to_id: dict[str, int] = {}
    category_names = sorted(
        {
            str(row.category).strip()
            for row in products
            if row.category and str(row.category).strip()
        }
    )
    for category_name in category_names:
        result = connection.execute(
            product_categories_table.insert().values(
                name=category_name,
                slug=_slugify(category_name),
            )
        )
        category_name_to_id[category_name] = int(result.inserted_primary_key[0])

    for row in products:
        external_product_id = None
        if isinstance(row.normalized_url, str):
            match = re.search(r"/product/\d+/(\d+)|/i\.\d+\.(\d+)", row.normalized_url)
            if match:
                external_product_id = match.group(1) or match.group(2)
            else:
                query_match = re.search(r"itemid=(\d+)", row.normalized_url)
                if query_match:
                    external_product_id = query_match.group(1)

        row_fingerprint = _fingerprint(
            marketplace="shopee",
            external_product_id=external_product_id,
            normalized_url=row.normalized_url or row.source_url,
        )
        connection.execute(
            products_table.update()
            .where(products_table.c.id == row.id)
            .values(
                external_product_id=external_product_id,
                fingerprint=row_fingerprint,
                aggregate_version=1,
            )
        )

        category_name = str(row.category).strip() if row.category else ""
        if category_name:
            connection.execute(
                products_table.update()
                .where(products_table.c.id == row.id)
                .values(category_id=category_name_to_id[category_name])
            )

        raw_images = row.images
        images: list[str] = []
        if isinstance(raw_images, list):
            images = [str(item) for item in raw_images if str(item).strip()]
        elif isinstance(raw_images, str):
            try:
                decoded = json.loads(raw_images)
                if isinstance(decoded, list):
                    images = [str(item) for item in decoded if str(item).strip()]
            except json.JSONDecodeError:
                images = []

        if images:
            connection.execute(
                product_images_table.insert(),
                [
                    {
                        "product_id": row.id,
                        "image_url": image,
                        "sort_order": index,
                    }
                    for index, image in enumerate(images)
                ],
            )

        connection.execute(
            product_price_histories_table.insert().values(
                product_id=row.id,
                price=row.price,
                original_price=row.original_price,
                discount=row.discount,
                captured_at=row.created_at or datetime.now(UTC),
            )
        )
        connection.execute(
            product_version_histories_table.insert().values(
                product_id=row.id,
                version=1,
                fingerprint=row_fingerprint,
                title=str(row.title).strip() or "Unknown Product",
                price=row.price,
                original_price=row.original_price,
                discount=row.discount,
                rating=row.rating,
                sold_count=row.sold_count,
                images=images,
                shop_name=row.shop_name,
                category=row.category,
                affiliate_url=row.affiliate_url,
                change_reason="import",
            )
        )

    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column(
            "normalized_url", existing_type=sa.String(length=2048), nullable=False
        )
        batch_op.alter_column(
            "fingerprint", existing_type=sa.String(length=64), nullable=False
        )
        if not _fk_exists("products", "fk_products_category_id_product_categories"):
            batch_op.create_foreign_key(
                "fk_products_category_id_product_categories",
                "product_categories",
                ["category_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint(
            "fk_products_category_id_product_categories", type_="foreignkey"
        )

    op.drop_index(
        "ix_product_version_histories_product_id_version",
        table_name="product_version_histories",
    )
    op.drop_index(
        "ix_product_version_histories_product_id",
        table_name="product_version_histories",
    )
    op.drop_index(
        "ix_product_version_histories_id", table_name="product_version_histories"
    )
    op.drop_table("product_version_histories")

    op.drop_index(
        "ix_product_price_histories_product_id_captured_at",
        table_name="product_price_histories",
    )
    op.drop_index(
        "ix_product_price_histories_product_id", table_name="product_price_histories"
    )
    op.drop_index("ix_product_price_histories_id", table_name="product_price_histories")
    op.drop_table("product_price_histories")

    op.drop_index(
        "ix_product_images_product_id_sort_order", table_name="product_images"
    )
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_index("ix_product_images_id", table_name="product_images")
    op.drop_table("product_images")

    op.drop_index("ix_product_categories_slug", table_name="product_categories")
    op.drop_index("ix_product_categories_id", table_name="product_categories")
    op.drop_table("product_categories")

    op.drop_index(
        "ix_products_marketplace_external_product_id",
        table_name="products",
    )

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_index("ix_products_category_id")
        batch_op.drop_index("ix_products_external_product_id")
        batch_op.drop_index("ix_products_aggregate_version")
        batch_op.drop_index("ix_products_fingerprint")
        batch_op.drop_index("ix_products_marketplace")
        batch_op.drop_index("ix_products_normalized_url")
        batch_op.drop_column("category_id")
        batch_op.drop_column("aggregate_version")
        batch_op.drop_column("fingerprint")
        batch_op.drop_column("external_product_id")
        batch_op.drop_column("marketplace")
        batch_op.drop_column("normalized_url")
