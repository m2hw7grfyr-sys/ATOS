"""Add execution center TGE scaffold.

Revision ID: 0007
Revises: 0006
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    profile_columns = {column["name"] for column in inspector.get_columns("tge_profiles")}
    with op.batch_alter_table("tge_profiles") as batch:
        if "connection_status" not in profile_columns:
            batch.add_column(sa.Column("connection_status", sa.String(length=40), nullable=False, server_default="'UNKNOWN'"))
            batch.create_index("ix_tge_profiles_connection_status", ["connection_status"])
        if "last_connection_test_at" not in profile_columns:
            batch.add_column(sa.Column("last_connection_test_at", sa.DateTime(timezone=True), nullable=True))
        if "last_connection_error" not in profile_columns:
            batch.add_column(sa.Column("last_connection_error", sa.Text(), nullable=True))
        if "runtime_status" not in profile_columns:
            batch.add_column(sa.Column("runtime_status", sa.String(length=40), nullable=False, server_default="'UNKNOWN'"))
            batch.create_index("ix_tge_profiles_runtime_status", ["runtime_status"])
        if "websocket_url" not in profile_columns:
            batch.add_column(sa.Column("websocket_url", sa.String(length=1000), nullable=True))
        if "debug_port" not in profile_columns:
            batch.add_column(sa.Column("debug_port", sa.Integer(), nullable=True))
        if "last_synced_at" not in profile_columns:
            batch.add_column(sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))

    if "execution_tasks" not in tables:
        op.create_table(
            "execution_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("scheduler_task_id", sa.Integer(), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("tge_profile_id", sa.Integer(), nullable=True),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("action_type", sa.String(length=60), nullable=False),
            sa.Column("strategy", sa.String(length=120), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=40), nullable=False),
            sa.Column("precheck_status", sa.String(length=40), nullable=False),
            sa.Column("environment_status", sa.String(length=40), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_code", sa.String(length=80), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["scheduler_task_id"], ["scheduler_tasks.id"]),
            sa.ForeignKeyConstraint(["tge_profile_id"], ["tge_profiles.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scheduler_task_id"),
        )
        for name, cols, unique in [
            ("ix_execution_tasks_uuid", ["uuid"], True),
            ("ix_execution_tasks_scheduler_task_id", ["scheduler_task_id"], True),
            ("ix_execution_tasks_account_id", ["account_id"], False),
            ("ix_execution_tasks_tge_profile_id", ["tge_profile_id"], False),
            ("ix_execution_tasks_platform", ["platform"], False),
            ("ix_execution_tasks_action_type", ["action_type"], False),
            ("ix_execution_tasks_status", ["status"], False),
            ("ix_execution_tasks_precheck_status", ["precheck_status"], False),
            ("ix_execution_tasks_environment_status", ["environment_status"], False),
            ("ix_execution_tasks_error_code", ["error_code"], False),
        ]:
            op.create_index(name, "execution_tasks", cols, unique=unique)

    if "execution_logs" not in tables:
        op.create_table(
            "execution_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("execution_task_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=100), nullable=False),
            sa.Column("old_status", sa.String(length=40), nullable=True),
            sa.Column("new_status", sa.String(length=40), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["execution_task_id"], ["execution_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_execution_logs_uuid", "execution_logs", ["uuid"], unique=True)
        op.create_index("ix_execution_logs_execution_task_id", "execution_logs", ["execution_task_id"])
        op.create_index("ix_execution_logs_action", "execution_logs", ["action"])
        op.create_index("ix_execution_logs_created_at", "execution_logs", ["created_at"])

    if "replay_files" not in tables:
        op.create_table(
            "replay_files",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("execution_task_id", sa.Integer(), nullable=False),
            sa.Column("screenshot_path", sa.String(length=1000), nullable=True),
            sa.Column("html_path", sa.String(length=1000), nullable=True),
            sa.Column("console_log_path", sa.String(length=1000), nullable=True),
            sa.Column("network_log_path", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["execution_task_id"], ["execution_tasks.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_replay_files_uuid", "replay_files", ["uuid"], unique=True)
        op.create_index("ix_replay_files_execution_task_id", "replay_files", ["execution_task_id"])


def downgrade() -> None:
    op.drop_table("replay_files")
    op.drop_table("execution_logs")
    op.drop_table("execution_tasks")
