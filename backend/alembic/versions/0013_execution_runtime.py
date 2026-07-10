"""Add execution runtime queue and worker nodes.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0013"
down_revision: Union[str, None] = "0012"
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

    if "worker_nodes" not in tables:
        op.create_table(
            "worker_nodes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="ONLINE"),
            sa.Column("host", sa.String(length=200), nullable=True),
            sa.Column("version", sa.String(length=60), nullable=False, server_default="local"),
            sa.Column("capability", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "name", "status", "last_heartbeat"]:
            _create_index_if_missing("worker_nodes", column, unique=column in {"uuid", "name"})

    for column in [
        sa.Column("queue_status", sa.String(length=40), nullable=False, server_default="NEW"),
        sa.Column("worker_node_id", sa.Integer(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    ]:
        _add_column_if_missing("execution_tasks", column)
    for column in ["queue_status", "worker_node_id"]:
        _create_index_if_missing("execution_tasks", column)

    if "execution_queue" not in tables:
        op.create_table(
            "execution_queue",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("scheduler_task_id", sa.Integer(), nullable=True),
            sa.Column("execution_task_id", sa.Integer(), nullable=False),
            sa.Column("worker_node_id", sa.Integer(), nullable=True),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="QUEUED"),
            sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["execution_task_id"], ["execution_tasks.id"]),
            sa.ForeignKeyConstraint(["scheduler_task_id"], ["scheduler_tasks.id"]),
            sa.ForeignKeyConstraint(["worker_node_id"], ["worker_nodes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("execution_task_id"),
        )
        for column in ["uuid", "scheduler_task_id", "execution_task_id", "worker_node_id", "priority", "status", "queued_at"]:
            _create_index_if_missing("execution_queue", column, unique=column in {"uuid", "execution_task_id"})

    if "replay_indexes" not in tables:
        op.create_table(
            "replay_indexes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("execution_task_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="INDEXED"),
            sa.Column("artifact_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("manifest_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["execution_task_id"], ["execution_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("execution_task_id"),
        )
        for column in ["uuid", "execution_task_id", "status", "created_at"]:
            _create_index_if_missing("replay_indexes", column, unique=column in {"uuid", "execution_task_id"})


def downgrade() -> None:
    op.drop_table("replay_indexes")
    op.drop_table("execution_queue")
    op.drop_table("worker_nodes")
