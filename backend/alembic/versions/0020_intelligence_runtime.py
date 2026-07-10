"""Add intelligence runtime performance tables.

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0020"
down_revision: Union[str, None] = "0019"
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


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    _add_column_if_missing("prompt_versions", sa.Column("performance_score", sa.Float(), nullable=False, server_default="0"))

    if "content_performance" not in tables:
        op.create_table(
            "content_performance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=True),
            sa.Column("reply_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("engagement", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("conversion", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.ForeignKeyConstraint(["reply_id"], ["replies.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "post_id", "reply_id", "platform", "score", "created_at"]:
            _create_index_if_missing("content_performance", column, unique=column == "uuid")

    if "reply_scores" not in tables:
        op.create_table(
            "reply_scores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("reply_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=True),
            sa.Column("relevance", sa.Float(), nullable=False, server_default="0"),
            sa.Column("quality", sa.Float(), nullable=False, server_default="0"),
            sa.Column("engagement", sa.Float(), nullable=False, server_default="0"),
            sa.Column("conversion", sa.Float(), nullable=False, server_default="0"),
            sa.Column("risk", sa.Float(), nullable=False, server_default="0"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["reply_id"], ["replies.id"]),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "reply_id", "post_id", "score", "status"]:
            _create_index_if_missing("reply_scores", column, unique=column == "uuid")

    if "strategy_performance" not in tables:
        op.create_table(
            "strategy_performance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("strategy", sa.String(length=120), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("tasks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failure", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("conversion", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            *_timestamps(),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "strategy", "platform", "status"]:
            _create_index_if_missing("strategy_performance", column, unique=column == "uuid")

    if "account_performance" not in tables:
        op.create_table(
            "account_performance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("tasks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failure", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("health_change", sa.Float(), nullable=False, server_default="0"),
            sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "account_id", "platform", "status"]:
            _create_index_if_missing("account_performance", column, unique=column == "uuid")

    if "platform_performance" not in tables:
        op.create_table(
            "platform_performance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("tasks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("reply_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("engagement_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            *_timestamps(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("platform"),
        )
        for column in ["uuid", "platform", "status"]:
            _create_index_if_missing("platform_performance", column, unique=column in {"uuid", "platform"})

    if "time_performance" not in tables:
        op.create_table(
            "time_performance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("day", sa.String(length=10), nullable=False),
            sa.Column("hour", sa.Integer(), nullable=False),
            sa.Column("tasks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            *_timestamps(),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "platform", "day", "hour", "success_rate", "status"]:
            _create_index_if_missing("time_performance", column, unique=column == "uuid")

    if "intelligence_recommendations" not in tables:
        op.create_table(
            "intelligence_recommendations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("recommendation_type", sa.String(length=80), nullable=False),
            sa.Column("title", sa.String(length=240), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("priority", sa.String(length=30), nullable=False, server_default="NORMAL"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="intelligence"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="OPEN"),
            *_timestamps(),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "recommendation_type", "priority", "score", "source", "status"]:
            _create_index_if_missing("intelligence_recommendations", column, unique=column == "uuid")

    if "reply_similarities" not in tables:
        op.create_table(
            "reply_similarities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("reply_id", sa.Integer(), nullable=False),
            sa.Column("compared_reply_id", sa.Integer(), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("method", sa.String(length=60), nullable=False, server_default="mock_token_overlap"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["reply_id"], ["replies.id"]),
            sa.ForeignKeyConstraint(["compared_reply_id"], ["replies.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "reply_id", "compared_reply_id", "similarity_score", "status"]:
            _create_index_if_missing("reply_similarities", column, unique=column == "uuid")

    if "experiments" not in tables:
        op.create_table(
            "experiments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("experiment_id", sa.String(length=120), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("strategy_a", sa.String(length=120), nullable=False),
            sa.Column("strategy_b", sa.String(length=120), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("winner", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="RUNNING"),
            *_timestamps(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("experiment_id"),
        )
        for column in ["uuid", "experiment_id", "platform", "status"]:
            _create_index_if_missing("experiments", column, unique=column in {"uuid", "experiment_id"})


def downgrade() -> None:
    pass
