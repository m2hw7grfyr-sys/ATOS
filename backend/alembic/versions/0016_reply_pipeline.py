"""Add semi-auto reply pipeline tables.

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0016"
down_revision: Union[str, None] = "0015"
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

    if "reply_tasks" not in tables:
        op.create_table(
            "reply_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("reply_id", sa.Integer(), nullable=False),
            sa.Column("scheduler_task_id", sa.Integer(), nullable=True),
            sa.Column("execution_task_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("reply_content", sa.Text(), nullable=False),
            sa.Column("execution_mode", sa.String(length=40), nullable=False, server_default="SEMI_AUTO"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="CREATED"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.ForeignKeyConstraint(["reply_id"], ["replies.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "uuid",
            "post_id",
            "reply_id",
            "scheduler_task_id",
            "execution_task_id",
            "platform",
            "account_id",
            "execution_mode",
            "status",
        ]:
            _create_index_if_missing("reply_tasks", column, unique=column == "uuid")

    _add_column_if_missing("scheduler_tasks", sa.Column("reply_task_id", sa.Integer(), nullable=True))
    _create_index_if_missing("scheduler_tasks", "reply_task_id")
    _add_column_if_missing("execution_tasks", sa.Column("reply_task_id", sa.Integer(), nullable=True))
    _create_index_if_missing("execution_tasks", "reply_task_id")


def downgrade() -> None:
    pass
