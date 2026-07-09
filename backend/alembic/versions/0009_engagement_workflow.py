"""Add engagement strategy and task workflow.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "engagement_strategies" not in tables:
        op.create_table(
            "engagement_strategies",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("strategy_type", sa.String(length=80), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("browse_count_min", sa.Integer(), nullable=False),
            sa.Column("browse_count_max", sa.Integer(), nullable=False),
            sa.Column("like_count_min", sa.Integer(), nullable=False),
            sa.Column("like_count_max", sa.Integer(), nullable=False),
            sa.Column("visit_profile_count_min", sa.Integer(), nullable=False),
            sa.Column("visit_profile_count_max", sa.Integer(), nullable=False),
            sa.Column("pause_min_seconds", sa.Integer(), nullable=False),
            sa.Column("pause_max_seconds", sa.Integer(), nullable=False),
            sa.Column("before_reply_enabled", sa.Boolean(), nullable=False),
            sa.Column("weight", sa.Integer(), nullable=False),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "platform", "strategy_type", "enabled", "before_reply_enabled", "status"]:
            op.create_index(f"ix_engagement_strategies_{column}", "engagement_strategies", [column], unique=column == "uuid")
    if "engagement_tasks" not in tables:
        op.create_table(
            "engagement_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("strategy_id", sa.Integer(), nullable=True),
            sa.Column("scheduler_task_id", sa.Integer(), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("source_type", sa.String(length=80), nullable=False),
            sa.Column("source_value", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("browse_target_count", sa.Integer(), nullable=False),
            sa.Column("like_target_count", sa.Integer(), nullable=False),
            sa.Column("visit_profile_target_count", sa.Integer(), nullable=False),
            sa.Column("browse_done_count", sa.Integer(), nullable=False),
            sa.Column("like_done_count", sa.Integer(), nullable=False),
            sa.Column("visit_profile_done_count", sa.Integer(), nullable=False),
            sa.Column("priority", sa.String(length=20), nullable=False),
            sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_code", sa.String(length=80), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["scheduler_task_id"], ["scheduler_tasks.id"]),
            sa.ForeignKeyConstraint(["strategy_id"], ["engagement_strategies.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "strategy_id", "scheduler_task_id", "account_id", "platform", "source_type", "status", "priority", "error_code"]:
            op.create_index(f"ix_engagement_tasks_{column}", "engagement_tasks", [column], unique=column == "uuid")


def downgrade() -> None:
    op.drop_table("engagement_tasks")
    op.drop_table("engagement_strategies")
