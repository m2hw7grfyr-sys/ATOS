"""Add LLM provider routing, prompt versions, and AI generation metrics.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011"
down_revision: Union[str, None] = "0010"
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "provider_routing" not in tables:
        op.create_table(
            "provider_routing",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("task_type", sa.String(length=40), nullable=False),
            sa.Column("strategy", sa.String(length=80), nullable=True),
            sa.Column("min_commercial_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_risk_score", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("preferred_provider_id", sa.Integer(), nullable=True),
            sa.Column("fallback_provider_id", sa.Integer(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["preferred_provider_id"], ["llm_providers.id"]),
            sa.ForeignKeyConstraint(["fallback_provider_id"], ["llm_providers.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "uuid",
            "platform",
            "task_type",
            "strategy",
            "preferred_provider_id",
            "fallback_provider_id",
            "enabled",
            "priority",
            "status",
        ]:
            _create_index_if_missing("provider_routing", column, unique=column == "uuid")

    if "prompt_versions" not in tables:
        op.create_table(
            "prompt_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("prompt_template_id", sa.Integer(), nullable=False),
            sa.Column("version", sa.String(length=40), nullable=False, server_default="v1"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("variables_schema", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("strategy", sa.String(length=80), nullable=True),
            sa.Column("tone", sa.String(length=80), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["prompt_template_id"], ["prompt_templates.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "uuid",
            "prompt_template_id",
            "platform",
            "strategy",
            "tone",
            "enabled",
            "is_default",
            "status",
        ]:
            _create_index_if_missing("prompt_versions", column, unique=column == "uuid")

    for column in [
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("fallback_provider_id", sa.Integer(), nullable=True),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("generation_source", sa.String(length=40), nullable=False, server_default="MOCK"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
    ]:
        _add_column_if_missing("ai_tasks", column)
    for column in ["provider_id", "fallback_provider_id", "prompt_version_id", "generation_source", "fallback_used"]:
        _create_index_if_missing("ai_tasks", column)

    for column in [
        sa.Column("health_status", sa.String(length=30), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_error", sa.Text(), nullable=True),
    ]:
        _add_column_if_missing("llm_providers", column)
    _create_index_if_missing("llm_providers", "health_status")

    for column in [
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("fallback_from_provider", sa.String(length=120), nullable=True),
        sa.Column("fallback_to_provider", sa.String(length=120), nullable=True),
    ]:
        _add_column_if_missing("ai_generation_logs", column)
    _create_index_if_missing("ai_generation_logs", "prompt_version_id")


def downgrade() -> None:
    op.drop_table("prompt_versions")
    op.drop_table("provider_routing")
