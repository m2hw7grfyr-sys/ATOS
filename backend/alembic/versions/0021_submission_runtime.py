"""Add submission runtime tables.

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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

    if "submission_tasks" not in tables:
        op.create_table(
            "submission_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("reply_task_id", sa.Integer(), nullable=True),
            sa.Column("execution_task_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("worker_id", sa.Integer(), nullable=True),
            sa.Column("browser_session_id", sa.Integer(), nullable=True),
            sa.Column("browser_tab_id", sa.Integer(), nullable=True),
            sa.Column("execution_mode", sa.String(length=40), nullable=False, server_default="SEMI_AUTO"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="CREATED"),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("result_url", sa.String(length=1000), nullable=True),
            sa.Column("result_external_id", sa.String(length=240), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_retry", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("manual_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["reply_task_id"], ["reply_tasks.id"]),
            sa.ForeignKeyConstraint(["execution_task_id"], ["execution_tasks.id"]),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["worker_id"], ["worker_nodes.id"]),
            sa.ForeignKeyConstraint(["browser_session_id"], ["browser_sessions.id"]),
            sa.ForeignKeyConstraint(["browser_tab_id"], ["browser_tabs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "uuid",
            "reply_task_id",
            "execution_task_id",
            "platform",
            "account_id",
            "worker_id",
            "browser_session_id",
            "browser_tab_id",
            "execution_mode",
            "status",
            "submitted_at",
            "verified_at",
            "result_external_id",
            "manual_confirmed",
        ]:
            _create_index_if_missing("submission_tasks", column, unique=column == "uuid")

    if "submission_logs" not in tables:
        op.create_table(
            "submission_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("submission_task_id", sa.Integer(), nullable=False),
            sa.Column("step", sa.String(length=100), nullable=False),
            sa.Column("level", sa.String(length=20), nullable=False, server_default="INFO"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("screenshot_path", sa.String(length=1000), nullable=True),
            sa.Column("html_snapshot_path", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["submission_task_id"], ["submission_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "submission_task_id", "step", "level", "created_at"]:
            _create_index_if_missing("submission_logs", column, unique=column == "uuid")


def downgrade() -> None:
    op.drop_table("submission_logs")
    op.drop_table("submission_tasks")
