"""create promotional images table

Revision ID: 20260719_0004
Revises: 20260719_0003
Create Date: 2026-07-19 01:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0004"
down_revision = "20260719_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promotional_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_name", sa.String(length=32), nullable=False),
        sa.Column("output_format", sa.String(length=8), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("product_image_url", sa.String(length=2048), nullable=False),
        sa.Column("shop_logo_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_promotional_images_id", "promotional_images", ["id"], unique=False)
    op.create_index("ix_promotional_images_product_id", "promotional_images", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_promotional_images_product_id", table_name="promotional_images")
    op.drop_index("ix_promotional_images_id", table_name="promotional_images")
    op.drop_table("promotional_images")
