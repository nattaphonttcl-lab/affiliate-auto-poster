"""create scheduler tables

Revision ID: 20260719_0005
Revises: 20260719_0004
Create Date: 2026-07-19 02:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0005"
down_revision = "20260719_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("caption_batch_id", sa.Integer(), sa.ForeignKey("caption_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "promotional_image_id",
            sa.Integer(),
            sa.ForeignKey("promotional_images.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scheduled_posts_id", "scheduled_posts", ["id"], unique=False)
    op.create_index("ix_scheduled_posts_product_id", "scheduled_posts", ["product_id"], unique=False)
    op.create_index("ix_scheduled_posts_caption_batch_id", "scheduled_posts", ["caption_batch_id"], unique=False)
    op.create_index("ix_scheduled_posts_promotional_image_id", "scheduled_posts", ["promotional_image_id"], unique=False)
    op.create_index("ix_scheduled_posts_scheduled_for", "scheduled_posts", ["scheduled_for"], unique=False)
    op.create_index("ix_scheduled_posts_status", "scheduled_posts", ["status"], unique=False)

    op.create_table(
        "scheduled_post_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduled_post_id", sa.Integer(), sa.ForeignKey("scheduled_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scheduled_post_executions_id", "scheduled_post_executions", ["id"], unique=False)
    op.create_index(
        "ix_scheduled_post_executions_scheduled_post_id",
        "scheduled_post_executions",
        ["scheduled_post_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_post_executions_scheduled_post_id", table_name="scheduled_post_executions")
    op.drop_index("ix_scheduled_post_executions_id", table_name="scheduled_post_executions")
    op.drop_table("scheduled_post_executions")

    op.drop_index("ix_scheduled_posts_status", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_scheduled_for", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_promotional_image_id", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_caption_batch_id", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_product_id", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_id", table_name="scheduled_posts")
    op.drop_table("scheduled_posts")
