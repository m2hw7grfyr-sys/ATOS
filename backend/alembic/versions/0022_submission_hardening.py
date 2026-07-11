"""Harden cross-platform submission fields.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    _add_column_if_missing("submission_tasks", sa.Column("post_id", sa.Integer(), nullable=True))
    _add_column_if_missing("submission_tasks", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("submission_tasks", sa.Column("operator_id", sa.String(length=120), nullable=True))
    _add_column_if_missing("submission_tasks", sa.Column("verification_level", sa.String(length=40), nullable=False, server_default="NONE"))
    _add_column_if_missing("submission_tasks", sa.Column("verification_status", sa.String(length=60), nullable=False, server_default="NONE"))
    _add_column_if_missing("submission_tasks", sa.Column("error_code", sa.String(length=80), nullable=True))
    _add_column_if_missing("submission_tasks", sa.Column("error_message", sa.Text(), nullable=True))
    _add_column_if_missing("submission_tasks", sa.Column("retry_blocked_reason", sa.Text(), nullable=True))
    for column in [
        "post_id",
        "confirmed_at",
        "operator_id",
        "verification_level",
        "verification_status",
        "error_code",
    ]:
        _create_index_if_missing("submission_tasks", column)


def downgrade() -> None:
    pass
