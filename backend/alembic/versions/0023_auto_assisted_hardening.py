"""Add auto assisted hardening configuration.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns(table)}
    if column.name not in columns:
        op.add_column(table, column)


def _create_index_if_missing(table: str, column: str) -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes(table)}
    name = f"ix_{table}_{column}"
    if name not in indexes:
        op.create_index(name, table, [column])


def upgrade() -> None:
    _add_column_if_missing(
        "accounts",
        sa.Column("allow_auto_assisted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _create_index_if_missing("accounts", "allow_auto_assisted")

    if not _table_exists("auto_assisted_platform_configs"):
        op.create_table(
            "auto_assisted_platform_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("auto_assisted_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("max_daily_auto_submit", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("allowed_accounts", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("allowed_time_window", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("enabled_by", sa.String(length=120), nullable=True),
            sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("platform", name="uq_auto_assisted_platform"),
        )
        for column in ["uuid", "platform", "auto_assisted_enabled", "status"]:
            _create_index_if_missing("auto_assisted_platform_configs", column)

    if not _table_exists("account_auto_submit_limits"):
        op.create_table(
            "account_auto_submit_limits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("daily_auto_submit_limit", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("auto_submitted_today", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_id", "platform", name="uq_account_auto_submit_limit"),
        )
        for column in ["uuid", "account_id", "platform", "status"]:
            _create_index_if_missing("account_auto_submit_limits", column)


def downgrade() -> None:
    pass
