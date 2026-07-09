"""Add Apify actor mapping and post normalization fields.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in columns:
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "actor_mappings" not in tables:
        op.create_table(
            "actor_mappings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("data_source_id", sa.Integer(), nullable=True),
            sa.Column("actor_id", sa.String(length=200), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("mapping_name", sa.String(length=160), nullable=False),
            sa.Column("title_path", sa.String(length=300), nullable=True),
            sa.Column("content_path", sa.String(length=300), nullable=True),
            sa.Column("url_path", sa.String(length=300), nullable=True),
            sa.Column("author_path", sa.String(length=300), nullable=True),
            sa.Column("author_id_path", sa.String(length=300), nullable=True),
            sa.Column("community_path", sa.String(length=300), nullable=True),
            sa.Column("source_post_id_path", sa.String(length=300), nullable=True),
            sa.Column("published_at_path", sa.String(length=300), nullable=True),
            sa.Column("score_path", sa.String(length=300), nullable=True),
            sa.Column("comment_count_path", sa.String(length=300), nullable=True),
            sa.Column("media_path", sa.String(length=300), nullable=True),
            sa.Column("language_path", sa.String(length=300), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "data_source_id", "actor_id", "platform", "enabled", "status"]:
            op.create_index(f"ix_actor_mappings_{column}", "actor_mappings", [column], unique=column == "uuid")

    _add_column_if_missing("posts", sa.Column("author_id", sa.String(length=160), nullable=True))
    _add_column_if_missing("posts", sa.Column("score", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("posts", sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("posts", sa.Column("media", sa.JSON(), nullable=False, server_default="[]"))
    _add_column_if_missing("posts", sa.Column("mapping_id", sa.Integer(), nullable=True))
    _add_column_if_missing("crawl_logs", sa.Column("mapping_id", sa.Integer(), nullable=True))
    _add_column_if_missing("crawl_logs", sa.Column("mapping_missing", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("crawl_logs", sa.Column("incomplete_count", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("crawl_logs", sa.Column("validation_failed_count", sa.Integer(), nullable=False, server_default="0"))
    _add_column_if_missing("crawl_logs", sa.Column("normalization_warning_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_table("actor_mappings")
