"""Add scheduler queue pipeline.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    with op.batch_alter_table("accounts") as batch:
        if "cooling_down_until" not in account_columns:
            batch.add_column(sa.Column("cooling_down_until", sa.DateTime(timezone=True), nullable=True))
        if "last_failure_reason" not in account_columns:
            batch.add_column(sa.Column("last_failure_reason", sa.Text(), nullable=True))
        if "failure_count_24h" not in account_columns:
            batch.add_column(sa.Column("failure_count_24h", sa.Integer(), nullable=False, server_default="0"))
        if "restriction_count_7d" not in account_columns:
            batch.add_column(sa.Column("restriction_count_7d", sa.Integer(), nullable=False, server_default="0"))
        if "auto_downgrade_enabled" not in account_columns:
            batch.add_column(sa.Column("auto_downgrade_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))

    scheduler_columns = {column["name"] for column in inspector.get_columns("scheduler_tasks")}
    with op.batch_alter_table("scheduler_tasks") as batch:
        if "earliest_execute_at" not in scheduler_columns:
            batch.add_column(sa.Column("earliest_execute_at", sa.DateTime(timezone=True), nullable=True))
            batch.create_index("ix_scheduler_tasks_earliest_execute_at", ["earliest_execute_at"], unique=False)
        if "delay_seconds" not in scheduler_columns:
            batch.add_column(sa.Column("delay_seconds", sa.Integer(), nullable=False, server_default="0"))
        if "error_message" not in scheduler_columns:
            batch.add_column(sa.Column("error_message", sa.Text(), nullable=True))

    if "scheduler_logs" not in tables:
        op.create_table(
            "scheduler_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("old_status", sa.String(length=30), nullable=True),
            sa.Column("new_status", sa.String(length=30), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("selected_account_id", sa.Integer(), nullable=True),
            sa.Column("delay_seconds", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["selected_account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["task_id"], ["scheduler_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_scheduler_logs_uuid", "scheduler_logs", ["uuid"], unique=True)
        op.create_index("ix_scheduler_logs_task_id", "scheduler_logs", ["task_id"])
        op.create_index("ix_scheduler_logs_action", "scheduler_logs", ["action"])
        op.create_index("ix_scheduler_logs_selected_account_id", "scheduler_logs", ["selected_account_id"])
        op.create_index("ix_scheduler_logs_created_at", "scheduler_logs", ["created_at"])

    if "platform_weights" not in tables:
        op.create_table(
            "platform_weights",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform_id", sa.Integer(), nullable=False),
            sa.Column("weight", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("platform_id"),
        )
        op.create_index("ix_platform_weights_uuid", "platform_weights", ["uuid"], unique=True)
        op.create_index("ix_platform_weights_platform_id", "platform_weights", ["platform_id"], unique=True)
        op.create_index("ix_platform_weights_enabled", "platform_weights", ["enabled"])
        op.create_index("ix_platform_weights_status", "platform_weights", ["status"])


def downgrade() -> None:
    op.drop_table("platform_weights")
    op.drop_table("scheduler_logs")
    with op.batch_alter_table("scheduler_tasks") as batch:
        batch.drop_index("ix_scheduler_tasks_earliest_execute_at")
        batch.drop_column("error_message")
        batch.drop_column("delay_seconds")
        batch.drop_column("earliest_execute_at")
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("auto_downgrade_enabled")
        batch.drop_column("restriction_count_7d")
        batch.drop_column("failure_count_24h")
        batch.drop_column("last_failure_reason")
        batch.drop_column("cooling_down_until")
