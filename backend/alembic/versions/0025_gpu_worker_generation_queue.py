"""Add GPU worker heartbeat and generation queue.

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def _create_index_if_missing(table: str, column: str, unique: bool = False) -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes(table)}
    name = f"ix_{table}_{column}"
    if name not in indexes:
        op.create_index(name, table, [column], unique=unique)


def upgrade() -> None:
    if not _table_exists("gpu_worker_statuses"):
        op.create_table(
            "gpu_worker_statuses",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_id", sa.String(length=120), nullable=False),
            sa.Column("worker_name", sa.String(length=160), nullable=False),
            sa.Column("worker_type", sa.String(length=60), nullable=False, server_default="gpu"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="offline"),
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.String(length=60), nullable=True),
            sa.Column("gpu_name", sa.String(length=160), nullable=True),
            sa.Column("gpu_memory_total_mb", sa.Integer(), nullable=True),
            sa.Column("gpu_memory_free_mb", sa.Integer(), nullable=True),
            sa.Column("ollama_version", sa.String(length=60), nullable=True),
            sa.Column("ollama_reachable", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("model_name", sa.String(length=160), nullable=True),
            sa.Column("current_task_id", sa.Integer(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("worker_id", name="uq_gpu_worker_status_worker_id"),
        )
        for column in [
            "worker_id",
            "worker_name",
            "worker_type",
            "status",
            "last_heartbeat_at",
            "model_name",
            "current_task_id",
            "created_at",
            "updated_at",
        ]:
            _create_index_if_missing("gpu_worker_statuses", column, unique=column == "worker_id")

    if not _table_exists("gpu_generation_tasks"):
        op.create_table(
            "gpu_generation_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("model", sa.String(length=160), nullable=False, server_default="llama3.1:8b"),
            sa.Column("options_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("result_text", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("error_type", sa.String(length=120), nullable=True),
            sa.Column("retryable", sa.Boolean(), nullable=True),
            sa.Column("worker_id", sa.String(length=120), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metrics_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "uuid",
            "status",
            "model",
            "worker_id",
            "lease_expires_at",
            "created_at",
            "started_at",
            "completed_at",
            "updated_at",
            "error_type",
        ]:
            _create_index_if_missing("gpu_generation_tasks", column, unique=column == "uuid")


def downgrade() -> None:
    pass
