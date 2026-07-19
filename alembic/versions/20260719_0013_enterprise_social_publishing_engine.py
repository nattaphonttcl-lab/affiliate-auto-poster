"""enterprise social publishing engine

Revision ID: 20260719_0013
Revises: 20260719_0012
Create Date: 2026-07-19 21:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0013"
down_revision = "20260719_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "timezone", sa.String(length=64), nullable=False, server_default="UTC"
        ),
        sa.Column("business_hours_start", sa.Integer(), nullable=True),
        sa.Column("business_hours_end", sa.Integer(), nullable=True),
        sa.Column(
            "rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"
        ),
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
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "owner_user_id",
            "platform",
            "account_identifier",
            name="uq_social_accounts_owner_platform_identifier",
        ),
    )
    op.create_index("ix_social_accounts_id", "social_accounts", ["id"])
    op.create_index(
        "ix_social_accounts_owner_user_id", "social_accounts", ["owner_user_id"]
    )
    op.create_index("ix_social_accounts_platform", "social_accounts", ["platform"])
    op.create_index(
        "ix_social_accounts_account_identifier",
        "social_accounts",
        ["account_identifier"],
    )

    op.create_table(
        "platform_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("social_account_id", sa.Integer(), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["social_account_id"], ["social_accounts.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_platform_credentials_id", "platform_credentials", ["id"])
    op.create_index(
        "ix_platform_credentials_social_account_id",
        "platform_credentials",
        ["social_account_id"],
    )

    op.create_table(
        "publishing_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("social_account_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("caption_content_id", sa.Integer(), nullable=True),
        sa.Column("generated_image_id", sa.Integer(), nullable=True),
        sa.Column("post_type", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("caption_text", sa.Text(), nullable=False),
        sa.Column("hashtags_text", sa.Text(), nullable=True),
        sa.Column("mentions_text", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.String(length=255), nullable=True),
        sa.Column("affiliate_link", sa.String(length=2048), nullable=True),
        sa.Column("alt_text", sa.String(length=500), nullable=True),
        sa.Column("provider_response", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recurrence_rule", sa.String(length=255), nullable=True),
        sa.Column(
            "timezone", sa.String(length=64), nullable=False, server_default="UTC"
        ),
        sa.Column(
            "business_hours_enforced",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["social_account_id"], ["social_accounts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["caption_content_id"], ["generated_contents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["generated_image_id"], ["generated_images.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_publishing_jobs_idempotency_key"
        ),
    )
    op.create_index("ix_publishing_jobs_id", "publishing_jobs", ["id"])
    op.create_index(
        "ix_publishing_jobs_owner_user_id", "publishing_jobs", ["owner_user_id"]
    )
    op.create_index(
        "ix_publishing_jobs_social_account_id", "publishing_jobs", ["social_account_id"]
    )
    op.create_index("ix_publishing_jobs_product_id", "publishing_jobs", ["product_id"])
    op.create_index(
        "ix_publishing_jobs_caption_content_id",
        "publishing_jobs",
        ["caption_content_id"],
    )
    op.create_index(
        "ix_publishing_jobs_generated_image_id",
        "publishing_jobs",
        ["generated_image_id"],
    )
    op.create_index("ix_publishing_jobs_platform", "publishing_jobs", ["platform"])
    op.create_index("ix_publishing_jobs_status", "publishing_jobs", ["status"])
    op.create_index("ix_publishing_jobs_post_type", "publishing_jobs", ["post_type"])
    op.create_index(
        "ix_publishing_jobs_idempotency_key", "publishing_jobs", ["idempotency_key"]
    )
    op.create_index(
        "ix_publishing_jobs_scheduled_for", "publishing_jobs", ["scheduled_for"]
    )
    op.create_index(
        "ix_publishing_jobs_next_retry_at", "publishing_jobs", ["next_retry_at"]
    )

    op.create_table(
        "publishing_queues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_owner", sa.String(length=128), nullable=True),
        sa.Column(
            "visible_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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
        sa.ForeignKeyConstraint(["job_id"], ["publishing_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_publishing_queues_job_id"),
    )
    op.create_index("ix_publishing_queues_id", "publishing_queues", ["id"])
    op.create_index("ix_publishing_queues_job_id", "publishing_queues", ["job_id"])
    op.create_index(
        "ix_publishing_queues_owner_user_id", "publishing_queues", ["owner_user_id"]
    )
    op.create_index("ix_publishing_queues_status", "publishing_queues", ["status"])
    op.create_index(
        "ix_publishing_queues_scheduled_for", "publishing_queues", ["scheduled_for"]
    )
    op.create_index(
        "ix_publishing_queues_visible_at", "publishing_queues", ["visible_at"]
    )

    op.create_table(
        "publishing_histories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("mentions", sa.Text(), nullable=True),
        sa.Column("cta", sa.String(length=255), nullable=True),
        sa.Column("affiliate_link", sa.String(length=2048), nullable=True),
        sa.Column("media_refs", sa.JSON(), nullable=False),
        sa.Column("provider_response", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "ctr", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"
        ),
        sa.Column(
            "conversion",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "revenue",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "commission",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["publishing_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_publishing_histories_id", "publishing_histories", ["id"])
    op.create_index(
        "ix_publishing_histories_job_id", "publishing_histories", ["job_id"]
    )
    op.create_index(
        "ix_publishing_histories_owner_user_id",
        "publishing_histories",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_publishing_histories_platform", "publishing_histories", ["platform"]
    )
    op.create_index(
        "ix_publishing_histories_status", "publishing_histories", ["status"]
    )

    op.create_table(
        "media_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("uri", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("thumbnail_uri", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["publishing_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_media_attachments_id", "media_attachments", ["id"])
    op.create_index("ix_media_attachments_job_id", "media_attachments", ["job_id"])
    op.create_index(
        "ix_media_attachments_media_type", "media_attachments", ["media_type"]
    )

    op.create_table(
        "publishing_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["publishing_jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_publishing_audit_logs_id", "publishing_audit_logs", ["id"])
    op.create_index(
        "ix_publishing_audit_logs_job_id", "publishing_audit_logs", ["job_id"]
    )
    op.create_index(
        "ix_publishing_audit_logs_owner_user_id",
        "publishing_audit_logs",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_publishing_audit_logs_action", "publishing_audit_logs", ["action"]
    )

    op.create_table(
        "publishing_dead_letter_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["publishing_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_publishing_dead_letter_queue_id", "publishing_dead_letter_queue", ["id"]
    )
    op.create_index(
        "ix_publishing_dead_letter_queue_job_id",
        "publishing_dead_letter_queue",
        ["job_id"],
    )
    op.create_index(
        "ix_publishing_dead_letter_queue_owner_user_id",
        "publishing_dead_letter_queue",
        ["owner_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_publishing_dead_letter_queue_owner_user_id",
        table_name="publishing_dead_letter_queue",
    )
    op.drop_index(
        "ix_publishing_dead_letter_queue_job_id",
        table_name="publishing_dead_letter_queue",
    )
    op.drop_index(
        "ix_publishing_dead_letter_queue_id", table_name="publishing_dead_letter_queue"
    )
    op.drop_table("publishing_dead_letter_queue")

    op.drop_index("ix_publishing_audit_logs_action", table_name="publishing_audit_logs")
    op.drop_index(
        "ix_publishing_audit_logs_owner_user_id", table_name="publishing_audit_logs"
    )
    op.drop_index("ix_publishing_audit_logs_job_id", table_name="publishing_audit_logs")
    op.drop_index("ix_publishing_audit_logs_id", table_name="publishing_audit_logs")
    op.drop_table("publishing_audit_logs")

    op.drop_index("ix_media_attachments_media_type", table_name="media_attachments")
    op.drop_index("ix_media_attachments_job_id", table_name="media_attachments")
    op.drop_index("ix_media_attachments_id", table_name="media_attachments")
    op.drop_table("media_attachments")

    op.drop_index("ix_publishing_histories_status", table_name="publishing_histories")
    op.drop_index("ix_publishing_histories_platform", table_name="publishing_histories")
    op.drop_index(
        "ix_publishing_histories_owner_user_id", table_name="publishing_histories"
    )
    op.drop_index("ix_publishing_histories_job_id", table_name="publishing_histories")
    op.drop_index("ix_publishing_histories_id", table_name="publishing_histories")
    op.drop_table("publishing_histories")

    op.drop_index("ix_publishing_queues_visible_at", table_name="publishing_queues")
    op.drop_index("ix_publishing_queues_scheduled_for", table_name="publishing_queues")
    op.drop_index("ix_publishing_queues_status", table_name="publishing_queues")
    op.drop_index("ix_publishing_queues_owner_user_id", table_name="publishing_queues")
    op.drop_index("ix_publishing_queues_job_id", table_name="publishing_queues")
    op.drop_index("ix_publishing_queues_id", table_name="publishing_queues")
    op.drop_table("publishing_queues")

    op.drop_index("ix_publishing_jobs_next_retry_at", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_scheduled_for", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_idempotency_key", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_post_type", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_status", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_platform", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_generated_image_id", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_caption_content_id", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_product_id", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_social_account_id", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_owner_user_id", table_name="publishing_jobs")
    op.drop_index("ix_publishing_jobs_id", table_name="publishing_jobs")
    op.drop_table("publishing_jobs")

    op.drop_index(
        "ix_platform_credentials_social_account_id", table_name="platform_credentials"
    )
    op.drop_index("ix_platform_credentials_id", table_name="platform_credentials")
    op.drop_table("platform_credentials")

    op.drop_index("ix_social_accounts_account_identifier", table_name="social_accounts")
    op.drop_index("ix_social_accounts_platform", table_name="social_accounts")
    op.drop_index("ix_social_accounts_owner_user_id", table_name="social_accounts")
    op.drop_index("ix_social_accounts_id", table_name="social_accounts")
    op.drop_table("social_accounts")
