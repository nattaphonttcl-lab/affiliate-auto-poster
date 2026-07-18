"""create caption tables

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19 01:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0003"
down_revision = "20260719_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caption_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("style", sa.String(length=32), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_caption_batches_id", "caption_batches", ["id"], unique=False)
    op.create_index("ix_caption_batches_product_id", "caption_batches", ["product_id"], unique=False)

    op.create_table(
        "captions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("caption_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("cta", sa.Text(), nullable=False),
        sa.Column("emoji", sa.String(length=16), nullable=False),
        sa.Column("hashtags", sa.Text(), nullable=False),
        sa.Column("caption_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_captions_id", "captions", ["id"], unique=False)
    op.create_index("ix_captions_batch_id", "captions", ["batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_captions_batch_id", table_name="captions")
    op.drop_index("ix_captions_id", table_name="captions")
    op.drop_table("captions")

    op.drop_index("ix_caption_batches_product_id", table_name="caption_batches")
    op.drop_index("ix_caption_batches_id", table_name="caption_batches")
    op.drop_table("caption_batches")
