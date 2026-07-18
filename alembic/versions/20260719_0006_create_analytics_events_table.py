"""create analytics events table

Revision ID: 20260719_0006
Revises: 20260719_0005
Create Date: 2026-07-19 02:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0006"
down_revision = "20260719_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_analytics_events_id", "analytics_events", ["id"], unique=False)
    op.create_index(
        "ix_analytics_events_event_type",
        "analytics_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_analytics_events_entity_type",
        "analytics_events",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        "ix_analytics_events_entity_id", "analytics_events", ["entity_id"], unique=False
    )
    op.create_index(
        "ix_analytics_events_occurred_at",
        "analytics_events",
        ["occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_events_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_entity_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_entity_type", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    op.drop_index("ix_analytics_events_id", table_name="analytics_events")
    op.drop_table("analytics_events")
