"""Add automation runtime worker pool and task locks.

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0019"
down_revision: Union[str, None] = "0018"
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
        sa.Column("worker_type", sa.String(length=60), nullable=False, server_default="LOCAL"),
        sa.Column("max_concurrent_tasks", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("health_score", sa.Float(), nullable=False, server_default="100"),
        sa.Column("failure_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("task_success_rate", sa.Float(), nullable=False, server_default="0"),
    ]:
        _add_column_if_missing("worker_nodes", column)
    for column in ["worker_type", "priority", "region"]:
        _create_index_if_missing("worker_nodes", column)

    for column in [
        sa.Column("claimed_by_worker", sa.String(length=120), nullable=True),
        sa.Column("max_retry", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_delay_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retry_strategy", sa.String(length=40), nullable=False, server_default="EXPONENTIAL"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_uuid", sa.String(length=36), nullable=True),
    ]:
        _add_column_if_missing("execution_tasks", column)
    for column in ["claimed_by_worker", "next_retry_at", "lock_uuid"]:
        _create_index_if_missing("execution_tasks", column)

    for column in [
        sa.Column("lock_uuid", sa.String(length=36), nullable=True),
        sa.Column("lock_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("required_capability", sa.String(length=80), nullable=True),
    ]:
        _add_column_if_missing("execution_queue", column)
    for column in ["lock_uuid", "lock_expires_at", "required_capability"]:
        _create_index_if_missing("execution_queue", column)

    for column in [
        sa.Column("execution_task_id", sa.Integer(), nullable=True),
        sa.Column("module", sa.String(length=80), nullable=False, server_default="worker"),
    ]:
        _add_column_if_missing("worker_logs", column)
    for column in ["execution_task_id", "module"]:
        _create_index_if_missing("worker_logs", column)

    if "task_locks" not in tables:
        op.create_table(
            "task_locks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("resource_type", sa.String(length=80), nullable=False, server_default="execution_task"),
            sa.Column("resource_id", sa.Integer(), nullable=False),
            sa.Column("owner_worker_id", sa.Integer(), nullable=True),
            sa.Column("lock_token", sa.String(length=80), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="ACTIVE"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_worker_id"], ["worker_nodes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "resource_type", "resource_id", "owner_worker_id", "lock_token", "status", "expires_at", "created_at"]:
            _create_index_if_missing("task_locks", column, unique=column in {"uuid", "lock_token"})

    if "runtime_metrics" not in tables:
        op.create_table(
            "runtime_metrics",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("metric", sa.String(length=120), nullable=False),
            sa.Column("value", sa.Float(), nullable=False, server_default="0"),
            sa.Column("dimension", sa.String(length=120), nullable=False, server_default="SYSTEM"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "metric", "dimension", "created_at"]:
            _create_index_if_missing("runtime_metrics", column, unique=column == "uuid")

    if "system_alerts" not in tables:
        op.create_table(
            "system_alerts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("alert_type", sa.String(length=80), nullable=False),
            sa.Column("severity", sa.String(length=40), nullable=False, server_default="WARNING"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="OPEN"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="automation"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "alert_type", "severity", "status", "source"]:
            _create_index_if_missing("system_alerts", column, unique=column == "uuid")


def downgrade() -> None:
    pass
