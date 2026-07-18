"""scheduler state machine and audit

Revision ID: 20260719_0008
Revises: 20260719_0007
Create Date: 2026-07-19 04:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0008"
down_revision = "20260719_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_posts") as batch_op:
        batch_op.add_column(
            sa.Column("owner_user_id", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column(
                "state",
                sa.String(length=32),
                nullable=False,
                server_default="awaiting_confirmation",
            )
        )
        batch_op.create_foreign_key(
            "fk_scheduled_posts_owner_user_id_users",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_scheduled_posts_owner_user_id", ["owner_user_id"], unique=False
        )
        batch_op.create_index("ix_scheduled_posts_state", ["state"], unique=False)

    op.execute("""
        UPDATE scheduled_posts
        SET state = CASE
            WHEN status = 'pending' AND is_confirmed = 1 THEN 'confirmed'
            WHEN status = 'pending' AND (is_confirmed = 0 OR is_confirmed IS NULL) THEN 'awaiting_confirmation'
            WHEN status = 'processing' THEN 'processing'
            WHEN status = 'published' THEN 'published'
            WHEN status = 'failed' THEN 'failed'
            ELSE 'awaiting_confirmation'
        END
        """)

    op.drop_index("ix_scheduled_posts_is_confirmed", table_name="scheduled_posts")
    op.drop_index("ix_scheduled_posts_status", table_name="scheduled_posts")

    with op.batch_alter_table("scheduled_posts") as batch_op:
        batch_op.drop_column("requires_confirmation")
        batch_op.drop_column("is_confirmed")
        batch_op.drop_column("confirmed_at")
        batch_op.drop_column("status")

    op.create_table(
        "scheduled_post_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheduled_post_id",
            sa.Integer(),
            sa.ForeignKey("scheduled_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=False),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_scheduled_post_audits_id", "scheduled_post_audits", ["id"], unique=False
    )
    op.create_index(
        "ix_scheduled_post_audits_scheduled_post_id",
        "scheduled_post_audits",
        ["scheduled_post_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_post_audits_actor_user_id",
        "scheduled_post_audits",
        ["actor_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_post_audits_actor_user_id", table_name="scheduled_post_audits"
    )
    op.drop_index(
        "ix_scheduled_post_audits_scheduled_post_id", table_name="scheduled_post_audits"
    )
    op.drop_index("ix_scheduled_post_audits_id", table_name="scheduled_post_audits")
    op.drop_table("scheduled_post_audits")

    with op.batch_alter_table("scheduled_posts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status", sa.String(length=24), nullable=False, server_default="pending"
            )
        )
        batch_op.add_column(
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(
            sa.Column(
                "requires_confirmation",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.create_index(
            "ix_scheduled_posts_is_confirmed", ["is_confirmed"], unique=False
        )

    op.execute("""
        UPDATE scheduled_posts
        SET status = CASE
            WHEN state = 'awaiting_confirmation' OR state = 'confirmed' THEN 'pending'
            WHEN state = 'processing' THEN 'processing'
            WHEN state = 'published' THEN 'published'
            WHEN state = 'failed' THEN 'failed'
            ELSE 'pending'
        END
        """)
    op.execute("""
        UPDATE scheduled_posts
        SET is_confirmed = CASE WHEN state = 'confirmed' THEN 1 ELSE 0 END
        """)

    with op.batch_alter_table("scheduled_posts") as batch_op:
        batch_op.drop_index("ix_scheduled_posts_state")
        batch_op.drop_index("ix_scheduled_posts_owner_user_id")
        batch_op.drop_constraint(
            "fk_scheduled_posts_owner_user_id_users",
            type_="foreignkey",
        )
        batch_op.drop_column("state")
        batch_op.drop_column("owner_user_id")
