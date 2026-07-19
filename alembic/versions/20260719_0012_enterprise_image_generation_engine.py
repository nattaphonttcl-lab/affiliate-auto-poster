"""enterprise image generation engine

Revision ID: 20260719_0012
Revises: 20260719_0011
Create Date: 2026-07-19 18:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260719_0012"
down_revision = "20260719_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("image_type", sa.String(length=64), nullable=False),
        sa.Column("canvas_width", sa.Integer(), nullable=False),
        sa.Column("canvas_height", sa.Integer(), nullable=False),
        sa.Column("safe_area", sa.JSON(), nullable=False),
        sa.Column("background", sa.JSON(), nullable=False),
        sa.Column("layers", sa.JSON(), nullable=False),
        sa.Column("fonts", sa.JSON(), nullable=False),
        sa.Column("colors", sa.JSON(), nullable=False),
        sa.Column("logo_position", sa.JSON(), nullable=False),
        sa.Column("watermark", sa.JSON(), nullable=False),
        sa.Column("overlay", sa.JSON(), nullable=False),
        sa.Column("dynamic_variables", sa.JSON(), nullable=False),
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
        sa.UniqueConstraint("name", "version", name="uq_image_templates_name_version"),
    )
    op.create_index("ix_image_templates_id", "image_templates", ["id"], unique=False)
    op.create_index(
        "ix_image_templates_name", "image_templates", ["name"], unique=False
    )
    op.create_index(
        "ix_image_templates_image_type", "image_templates", ["image_type"], unique=False
    )
    op.create_index(
        "ix_image_templates_status", "image_templates", ["status"], unique=False
    )
    op.create_index(
        "ix_image_templates_created_by", "image_templates", ["created_by"], unique=False
    )

    op.create_table(
        "image_provider_configs",
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
        "ix_image_provider_configs_id", "image_provider_configs", ["id"], unique=False
    )
    op.create_index(
        "ix_image_provider_configs_provider",
        "image_provider_configs",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_image_provider_configs_model",
        "image_provider_configs",
        ["model"],
        unique=False,
    )
    op.create_index(
        "ix_image_provider_configs_is_active",
        "image_provider_configs",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "image_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.String(length=2048), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_image_assets_id", "image_assets", ["id"], unique=False)
    op.create_index(
        "ix_image_assets_asset_type", "image_assets", ["asset_type"], unique=False
    )
    op.create_index("ix_image_assets_name", "image_assets", ["name"], unique=False)
    op.create_index(
        "ix_image_assets_checksum", "image_assets", ["checksum"], unique=False
    )
    op.create_index(
        "ix_image_assets_is_active", "image_assets", ["is_active"], unique=False
    )
    op.create_index(
        "ix_image_assets_created_by", "image_assets", ["created_by"], unique=False
    )

    op.create_table(
        "generated_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("caption_source_id", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("image_type", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=False,
            server_default="0",
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
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["caption_source_id"], ["generated_contents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["image_templates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_generated_images_id", "generated_images", ["id"], unique=False)
    op.create_index(
        "ix_generated_images_product_id",
        "generated_images",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_images_caption_source_id",
        "generated_images",
        ["caption_source_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_images_template_id",
        "generated_images",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_images_image_type",
        "generated_images",
        ["image_type"],
        unique=False,
    )
    op.create_index(
        "ix_generated_images_provider", "generated_images", ["provider"], unique=False
    )
    op.create_index(
        "ix_generated_images_owner_user_id",
        "generated_images",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "generated_image_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_image_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("rendered_variables", sa.JSON(), nullable=False),
        sa.Column("output_format", sa.String(length=16), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("image_uri", sa.String(length=2048), nullable=False),
        sa.Column("preview_uri", sa.String(length=2048), nullable=False),
        sa.Column("thumbnail_uri", sa.String(length=2048), nullable=False),
        sa.Column(
            "cost_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["generated_image_id"], ["generated_images.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "generated_image_id",
            "version",
            name="uq_generated_image_versions_image_version",
        ),
    )
    op.create_index(
        "ix_generated_image_versions_id",
        "generated_image_versions",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_image_versions_generated_image_id",
        "generated_image_versions",
        ["generated_image_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_image_versions_file_hash",
        "generated_image_versions",
        ["file_hash"],
        unique=False,
    )
    op.create_index(
        "ix_generated_image_versions_owner_user_id",
        "generated_image_versions",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "image_histories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generated_image_id", sa.Integer(), nullable=False),
        sa.Column("generated_image_version_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["generated_image_id"], ["generated_images.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["generated_image_version_id"],
            ["generated_image_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_image_histories_id", "image_histories", ["id"], unique=False)
    op.create_index(
        "ix_image_histories_generated_image_id",
        "image_histories",
        ["generated_image_id"],
        unique=False,
    )
    op.create_index(
        "ix_image_histories_generated_image_version_id",
        "image_histories",
        ["generated_image_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_image_histories_action", "image_histories", ["action"], unique=False
    )
    op.create_index(
        "ix_image_histories_owner_user_id",
        "image_histories",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_image_histories_owner_user_id", table_name="image_histories")
    op.drop_index("ix_image_histories_action", table_name="image_histories")
    op.drop_index(
        "ix_image_histories_generated_image_version_id", table_name="image_histories"
    )
    op.drop_index("ix_image_histories_generated_image_id", table_name="image_histories")
    op.drop_index("ix_image_histories_id", table_name="image_histories")
    op.drop_table("image_histories")

    op.drop_index(
        "ix_generated_image_versions_owner_user_id",
        table_name="generated_image_versions",
    )
    op.drop_index(
        "ix_generated_image_versions_file_hash", table_name="generated_image_versions"
    )
    op.drop_index(
        "ix_generated_image_versions_generated_image_id",
        table_name="generated_image_versions",
    )
    op.drop_index(
        "ix_generated_image_versions_id", table_name="generated_image_versions"
    )
    op.drop_table("generated_image_versions")

    op.drop_index("ix_generated_images_owner_user_id", table_name="generated_images")
    op.drop_index("ix_generated_images_provider", table_name="generated_images")
    op.drop_index("ix_generated_images_image_type", table_name="generated_images")
    op.drop_index("ix_generated_images_template_id", table_name="generated_images")
    op.drop_index(
        "ix_generated_images_caption_source_id", table_name="generated_images"
    )
    op.drop_index("ix_generated_images_product_id", table_name="generated_images")
    op.drop_index("ix_generated_images_id", table_name="generated_images")
    op.drop_table("generated_images")

    op.drop_index("ix_image_assets_created_by", table_name="image_assets")
    op.drop_index("ix_image_assets_is_active", table_name="image_assets")
    op.drop_index("ix_image_assets_checksum", table_name="image_assets")
    op.drop_index("ix_image_assets_name", table_name="image_assets")
    op.drop_index("ix_image_assets_asset_type", table_name="image_assets")
    op.drop_index("ix_image_assets_id", table_name="image_assets")
    op.drop_table("image_assets")

    op.drop_index(
        "ix_image_provider_configs_is_active", table_name="image_provider_configs"
    )
    op.drop_index(
        "ix_image_provider_configs_model", table_name="image_provider_configs"
    )
    op.drop_index(
        "ix_image_provider_configs_provider", table_name="image_provider_configs"
    )
    op.drop_index("ix_image_provider_configs_id", table_name="image_provider_configs")
    op.drop_table("image_provider_configs")

    op.drop_index("ix_image_templates_created_by", table_name="image_templates")
    op.drop_index("ix_image_templates_status", table_name="image_templates")
    op.drop_index("ix_image_templates_image_type", table_name="image_templates")
    op.drop_index("ix_image_templates_name", table_name="image_templates")
    op.drop_index("ix_image_templates_id", table_name="image_templates")
    op.drop_table("image_templates")
