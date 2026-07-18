"""add outbox and optimistic locking

Revision ID: 20260719_0009
Revises: 20260719_0008
Create Date: 2026-07-19 08:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0009"
down_revision = "20260719_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_posts") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.create_index("ix_scheduled_posts_version", ["version"], unique=False)
        batch_op.create_index(
            "ix_scheduled_posts_owner_state_scheduled_for",
            ["owner_user_id", "state", "scheduled_for"],
            unique=False,
        )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending"
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_outbox_events_id", "outbox_events", ["id"], unique=False)
    op.create_index(
        "ix_outbox_events_aggregate_type",
        "outbox_events",
        ["aggregate_type"],
        unique=False,
    )
    op.create_index(
        "ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"], unique=False
    )
    op.create_index(
        "ix_outbox_events_event_type", "outbox_events", ["event_type"], unique=False
    )
    op.create_index(
        "ix_outbox_events_status", "outbox_events", ["status"], unique=False
    )
    op.create_index(
        "ix_outbox_events_status_occurred_at",
        "outbox_events",
        ["status", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_status_occurred_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_id", table_name="outbox_events")
    op.drop_table("outbox_events")

    with op.batch_alter_table("scheduled_posts") as batch_op:
        batch_op.drop_index("ix_scheduled_posts_owner_state_scheduled_for")
        batch_op.drop_index("ix_scheduled_posts_version")
        batch_op.drop_column("version")
