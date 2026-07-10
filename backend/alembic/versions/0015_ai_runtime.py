"""Add AI Runtime generation log fields.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0015"
down_revision: Union[str, None] = "0014"
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
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("provider_type", sa.String(length=40), nullable=True),
        sa.Column("model_name", sa.String(length=160), nullable=True),
        sa.Column("task_type", sa.String(length=60), nullable=True),
        sa.Column("prompt_template_id", sa.Integer(), nullable=True),
        sa.Column("final_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=80), nullable=True),
    ]:
        _add_column_if_missing("ai_generation_logs", column)
    for column in [
        "provider_id",
        "provider_type",
        "task_type",
        "prompt_template_id",
        "final_prompt_hash",
        "error_code",
    ]:
        _create_index_if_missing("ai_generation_logs", column)


def downgrade() -> None:
    pass
