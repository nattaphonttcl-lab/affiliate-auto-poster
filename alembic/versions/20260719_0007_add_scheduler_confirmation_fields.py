"""add scheduler confirmation fields

Revision ID: 20260719_0007
Revises: 20260719_0006
Create Date: 2026-07-19 03:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0007"
down_revision = "20260719_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduled_posts",
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "scheduled_posts",
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "scheduled_posts",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_scheduled_posts_is_confirmed", "scheduled_posts", ["is_confirmed"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scheduled_posts_is_confirmed", table_name="scheduled_posts")
    op.drop_column("scheduled_posts", "confirmed_at")
    op.drop_column("scheduled_posts", "is_confirmed")
    op.drop_column("scheduled_posts", "requires_confirmation")
