"""Add reply templates and funnel strategy layer.

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0024"
down_revision: Union[str, None] = "0023"
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
    if not _table_exists("reply_templates"):
        op.create_table(
            "reply_templates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("name_cn", sa.String(length=120), nullable=False),
            sa.Column("name_en", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("funnel_intent", sa.String(length=60), nullable=False),
            sa.Column("cta_strength", sa.String(length=30), nullable=False, server_default="NONE"),
            sa.Column("default_platforms", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("risk_level", sa.String(length=40), nullable=False, server_default="LOW"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("funnel_intent", name="uq_reply_template_funnel_intent"),
        )
        for column in ["uuid", "name_cn", "name_en", "funnel_intent", "cta_strength", "risk_level", "enabled", "status"]:
            _create_index_if_missing("reply_templates", column)

    if not _table_exists("platform_template_rules"):
        op.create_table(
            "platform_template_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("template_id", sa.Integer(), nullable=False),
            sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("max_daily_ratio", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("risk_level", sa.String(length=40), nullable=False, server_default="LOW"),
            sa.Column("allow_auto_assisted", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["template_id"], ["reply_templates.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("platform", "template_id", name="uq_platform_template_rule"),
        )
        for column in ["uuid", "platform", "template_id", "allowed", "default_enabled", "risk_level", "allow_auto_assisted", "status"]:
            _create_index_if_missing("platform_template_rules", column)

    if not _table_exists("reply_template_performance"):
        op.create_table(
            "reply_template_performance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("template_id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("date", sa.String(length=10), nullable=False),
            sa.Column("generated_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("submitted_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("verified_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("engagement_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("conversion_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("failure_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["template_id"], ["reply_templates.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("template_id", "platform", "date", name="uq_template_performance_day"),
        )
        for column in ["uuid", "template_id", "platform", "date", "status"]:
            _create_index_if_missing("reply_template_performance", column)

    additions = [
        sa.Column("reply_template_id", sa.Integer(), nullable=True),
        sa.Column("funnel_intent", sa.String(length=60), nullable=True),
        sa.Column("cta_strength", sa.String(length=30), nullable=True),
        sa.Column("template_selection_reason", sa.Text(), nullable=True),
        sa.Column("link_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("profile_redirect_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("main_account_redirect_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("direct_link_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]
    for column in additions:
        _add_column_if_missing("reply_tasks", column)
    for column in [
        "reply_template_id",
        "funnel_intent",
        "cta_strength",
        "link_allowed",
        "profile_redirect_allowed",
        "main_account_redirect_allowed",
        "direct_link_allowed",
    ]:
        _create_index_if_missing("reply_tasks", column)


def downgrade() -> None:
    pass
