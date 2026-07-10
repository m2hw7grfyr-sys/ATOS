"""Add platform runtime registry.

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0018"
down_revision: Union[str, None] = "0017"
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
    if "platform_registry" not in tables:
        op.create_table(
            "platform_registry",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform_name", sa.String(length=80), nullable=False),
            sa.Column("adapter_name", sa.String(length=120), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("version", sa.String(length=40), nullable=False, server_default="v1"),
            sa.Column("capabilities", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="HEALTHY"),
            sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "platform_name", "adapter_name", "enabled", "status"]:
            _create_index_if_missing("platform_registry", column, unique=column in {"uuid", "platform_name"})

    _add_column_if_missing("platform_selectors", sa.Column("action_type", sa.String(length=80), nullable=True))
    _add_column_if_missing("platform_selectors", sa.Column("version", sa.String(length=40), nullable=False, server_default="v1"))
    _create_index_if_missing("platform_selectors", "action_type")


def downgrade() -> None:
    pass
