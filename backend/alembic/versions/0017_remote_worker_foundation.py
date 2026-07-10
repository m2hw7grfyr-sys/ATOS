"""Add remote worker foundation fields.

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0017"
down_revision: Union[str, None] = "0016"
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
    for column in [
        sa.Column("hostname", sa.String(length=200), nullable=True),
        sa.Column("os", sa.String(length=120), nullable=True),
        sa.Column("ip", sa.String(length=80), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("cpu", sa.Float(), nullable=True),
        sa.Column("memory", sa.Float(), nullable=True),
        sa.Column("gpu", sa.Float(), nullable=True),
        sa.Column("runtime_status", sa.String(length=60), nullable=False, server_default="UNKNOWN"),
        sa.Column("token_version", sa.String(length=40), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
    ]:
        _add_column_if_missing("worker_nodes", column)
    for column in ["hostname", "ip", "runtime_status", "last_seen"]:
        _create_index_if_missing("worker_nodes", column)

    inspector = sa.inspect(op.get_bind())
    if "worker_logs" not in set(inspector.get_table_names()):
        op.create_table(
            "worker_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("worker_node_id", sa.Integer(), nullable=True),
            sa.Column("worker_id", sa.String(length=120), nullable=True),
            sa.Column("log_type", sa.String(length=60), nullable=False, server_default="application"),
            sa.Column("level", sa.String(length=30), nullable=False, server_default="INFO"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["worker_node_id"], ["worker_nodes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "worker_node_id", "worker_id", "log_type", "level", "created_at"]:
            _create_index_if_missing("worker_logs", column, unique=column == "uuid")


def downgrade() -> None:
    pass
