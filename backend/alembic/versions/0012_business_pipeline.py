"""Add business pipeline state, events, timeline, and scheduler source fields.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in columns:
        op.add_column(table, column)


def _create_index_if_missing(table: str, column: str, unique: bool = False) -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes(table)}
    name = f"ix_{table}_{column}"
    if name not in indexes:
        op.create_index(name, table, [column], unique=unique)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    for column in [
        sa.Column("pipeline_stage", sa.String(length=40), nullable=False, server_default="NEW"),
        sa.Column("ready_for_ai_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    ]:
        _add_column_if_missing("posts", column)
    _create_index_if_missing("posts", "pipeline_stage")

    for column in [
        sa.Column("ai_task_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=60), nullable=False, server_default="MANUAL"),
    ]:
        _add_column_if_missing("scheduler_tasks", column)
    _create_index_if_missing("scheduler_tasks", "ai_task_id")
    _create_index_if_missing("scheduler_tasks", "source")

    if "post_timelines" not in tables:
        op.create_table(
            "post_timelines",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("event_name", sa.String(length=120), nullable=False),
            sa.Column("old_status", sa.String(length=40), nullable=True),
            sa.Column("new_status", sa.String(length=40), nullable=False),
            sa.Column("actor", sa.String(length=120), nullable=False, server_default="system"),
            sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "post_id", "event_name", "new_status", "created_at"]:
            _create_index_if_missing("post_timelines", column, unique=column == "uuid")

    if "business_events" not in tables:
        op.create_table(
            "business_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("event_name", sa.String(length=120), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("post_id", sa.Integer(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PUBLISHED"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "event_name", "entity_type", "entity_id", "post_id", "status", "created_at"]:
            _create_index_if_missing("business_events", column, unique=column == "uuid")

    if "filter_presets" not in tables:
        op.create_table(
            "filter_presets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("scope", sa.String(length=60), nullable=False),
            sa.Column("filters", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("actor", sa.String(length=120), nullable=False, server_default="system"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "scope", "status"]:
            _create_index_if_missing("filter_presets", column, unique=column == "uuid")


def downgrade() -> None:
    op.drop_table("filter_presets")
    op.drop_table("business_events")
    op.drop_table("post_timelines")
