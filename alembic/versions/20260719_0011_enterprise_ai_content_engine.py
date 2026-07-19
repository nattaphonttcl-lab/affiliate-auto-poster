"""enterprise ai content engine

Revision ID: 20260719_0011
Revises: 20260719_0010
Create Date: 2026-07-19 12:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0011"
down_revision = "20260719_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("temperature", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "category", "version", name="uq_prompt_templates_category_version"
        ),
    )
    op.create_index("ix_prompt_templates_id", "prompt_templates", ["id"], unique=False)
    op.create_index(
        "ix_prompt_templates_category", "prompt_templates", ["category"], unique=False
    )
    op.create_index(
        "ix_prompt_templates_status", "prompt_templates", ["status"], unique=False
    )
    op.create_index(
        "ix_prompt_templates_created_by",
        "prompt_templates",
        ["created_by"],
        unique=False,
    )

    op.create_table(
        "prompt_variables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_value", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"], ["prompt_templates.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_prompt_variables_id", "prompt_variables", ["id"], unique=False)
    op.create_index(
        "ix_prompt_variables_template_id",
        "prompt_variables",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_variables_name", "prompt_variables", ["name"], unique=False
    )

    op.create_table(
        "ai_provider_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
    op.create_index(
        "ix_ai_provider_configs_id", "ai_provider_configs", ["id"], unique=False
    )
    op.create_index(
        "ix_ai_provider_configs_provider",
        "ai_provider_configs",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_ai_provider_configs_model", "ai_provider_configs", ["model"], unique=False
    )
    op.create_index(
        "ix_ai_provider_configs_is_active",
        "ai_provider_configs",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "generated_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("style", sa.String(length=64), nullable=False),
        sa.Column("target_audience", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["prompt_templates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_generated_contents_id", "generated_contents", ["id"], unique=False
    )
    op.create_index(
        "ix_generated_contents_product_id",
        "generated_contents",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_contents_template_id",
        "generated_contents",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_contents_platform",
        "generated_contents",
        ["platform"],
        unique=False,
    )
    op.create_index(
        "ix_generated_contents_style", "generated_contents", ["style"], unique=False
    )
    op.create_index(
        "ix_generated_contents_target_audience",
        "generated_contents",
        ["target_audience"],
        unique=False,
    )
    op.create_index(
        "ix_generated_contents_provider",
        "generated_contents",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_generated_contents_created_by",
        "generated_contents",
        ["created_by"],
        unique=False,
    )

    op.create_table(
        "generated_content_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("prompt_rendered", sa.Text(), nullable=False),
        sa.Column("generated_text", sa.JSON(), nullable=False),
        sa.Column(
            "cost_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_id"], ["generated_contents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "content_id",
            "version",
            name="uq_generated_content_versions_content_version",
        ),
    )
    op.create_index(
        "ix_generated_content_versions_id",
        "generated_content_versions",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_content_versions_content_id",
        "generated_content_versions",
        ["content_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_content_versions_created_by",
        "generated_content_versions",
        ["created_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_content_versions_created_by",
        table_name="generated_content_versions",
    )
    op.drop_index(
        "ix_generated_content_versions_content_id",
        table_name="generated_content_versions",
    )
    op.drop_index(
        "ix_generated_content_versions_id", table_name="generated_content_versions"
    )
    op.drop_table("generated_content_versions")

    op.drop_index("ix_generated_contents_created_by", table_name="generated_contents")
    op.drop_index("ix_generated_contents_provider", table_name="generated_contents")
    op.drop_index(
        "ix_generated_contents_target_audience", table_name="generated_contents"
    )
    op.drop_index("ix_generated_contents_style", table_name="generated_contents")
    op.drop_index("ix_generated_contents_platform", table_name="generated_contents")
    op.drop_index("ix_generated_contents_template_id", table_name="generated_contents")
    op.drop_index("ix_generated_contents_product_id", table_name="generated_contents")
    op.drop_index("ix_generated_contents_id", table_name="generated_contents")
    op.drop_table("generated_contents")

    op.drop_index("ix_ai_provider_configs_is_active", table_name="ai_provider_configs")
    op.drop_index("ix_ai_provider_configs_model", table_name="ai_provider_configs")
    op.drop_index("ix_ai_provider_configs_provider", table_name="ai_provider_configs")
    op.drop_index("ix_ai_provider_configs_id", table_name="ai_provider_configs")
    op.drop_table("ai_provider_configs")

    op.drop_index("ix_prompt_variables_name", table_name="prompt_variables")
    op.drop_index("ix_prompt_variables_template_id", table_name="prompt_variables")
    op.drop_index("ix_prompt_variables_id", table_name="prompt_variables")
    op.drop_table("prompt_variables")

    op.drop_index("ix_prompt_templates_created_by", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_status", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_category", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_id", table_name="prompt_templates")
    op.drop_table("prompt_templates")
