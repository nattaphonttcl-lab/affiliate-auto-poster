"""create products table

Revision ID: 20260719_0002
Revises: 20260719_0001
Create Date: 2026-07-19 00:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0002"
down_revision = "20260719_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("original_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("discount", sa.String(length=64), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("sold_count", sa.Integer(), nullable=True),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("shop_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("affiliate_url", sa.String(length=2048), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_products_source_url", "products", ["source_url"], unique=True)
    op.create_index("ix_products_expires_at", "products", ["expires_at"], unique=False)
    op.create_index("ix_products_id", "products", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_id", table_name="products")
    op.drop_index("ix_products_expires_at", table_name="products")
    op.drop_index("ix_products_source_url", table_name="products")
    op.drop_table("products")
