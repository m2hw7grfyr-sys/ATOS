"""Add Apify data pipeline storage.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    post_columns = {column["name"] for column in inspector.get_columns("posts")}

    # Revision 0001 used current metadata. These guards support both an old
    # v0.1 database and a brand-new database built from the latest models.
    if "url_hash" not in post_columns:
        with op.batch_alter_table("posts") as batch:
            batch.alter_column(
                "source_post_id",
                existing_type=sa.String(length=160),
                nullable=True,
            )
            batch.add_column(sa.Column("url_hash", sa.String(length=64), nullable=True))
            batch.add_column(
                sa.Column("raw_json", sa.JSON(), nullable=False, server_default="{}")
            )
            batch.create_index("ix_posts_url_hash", ["url_hash"], unique=False)
            batch.create_unique_constraint(
                "uq_posts_platform_source_post", ["platform_id", "source_post_id"]
            )
            batch.create_unique_constraint(
                "uq_posts_platform_url_hash", ["platform_id", "url_hash"]
            )

    if "crawl_logs" not in inspector.get_table_names():
        op.create_table(
            "crawl_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("data_source_id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("actor_id", sa.String(length=200), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("total_items", sa.Integer(), nullable=False),
            sa.Column("inserted_count", sa.Integer(), nullable=False),
            sa.Column("duplicate_count", sa.Integer(), nullable=False),
            sa.Column("error_count", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("raw_response_excerpt", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_crawl_logs_uuid", "crawl_logs", ["uuid"], unique=True)
        op.create_index(
            "ix_crawl_logs_data_source_id",
            "crawl_logs",
            ["data_source_id"],
            unique=False,
        )
        op.create_index(
            "ix_crawl_logs_platform", "crawl_logs", ["platform"], unique=False
        )
        op.create_index(
            "ix_crawl_logs_actor_id", "crawl_logs", ["actor_id"], unique=False
        )
        op.create_index("ix_crawl_logs_status", "crawl_logs", ["status"], unique=False)
        op.create_index(
            "ix_crawl_logs_started_at", "crawl_logs", ["started_at"], unique=False
        )


def downgrade() -> None:
    op.drop_table("crawl_logs")
    with op.batch_alter_table("posts") as batch:
        batch.drop_constraint("uq_posts_platform_url_hash", type_="unique")
        batch.drop_constraint("uq_posts_platform_source_post", type_="unique")
        batch.drop_index("ix_posts_url_hash")
        batch.drop_column("raw_json")
        batch.drop_column("url_hash")
        batch.alter_column(
            "source_post_id",
            existing_type=sa.String(length=160),
            nullable=False,
        )
