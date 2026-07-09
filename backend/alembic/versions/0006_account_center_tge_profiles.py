"""Add account center and TGE profile binding.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    with op.batch_alter_table("accounts") as batch:
        additions = [
            ("profile_url", sa.String(length=1000), None),
            ("account_level", sa.String(length=60), None),
            ("karma_score", sa.Integer(), "0"),
            ("followers_count", sa.Integer(), "0"),
            ("following_count", sa.Integer(), "0"),
            ("account_age_days", sa.Integer(), "0"),
            ("risk_status", sa.String(length=30), "'LOW'"),
            ("remark", sa.Text(), None),
        ]
        for name, column_type, default in additions:
            if name not in account_columns:
                batch.add_column(
                    sa.Column(name, column_type, nullable=default is None, server_default=sa.text(default) if default else None)
                )
        if "risk_status" not in account_columns:
            batch.create_index("ix_accounts_risk_status", ["risk_status"], unique=False)

    profile_columns = {column["name"] for column in inspector.get_columns("tge_profiles")}
    with op.batch_alter_table("tge_profiles") as batch:
        if "bound_account_id" not in profile_columns:
            batch.add_column(sa.Column("bound_account_id", sa.Integer(), nullable=True))
            batch.create_index("ix_tge_profiles_bound_account_id", ["bound_account_id"], unique=True)
            batch.create_foreign_key("fk_tge_profiles_bound_account_id_accounts", "accounts", ["bound_account_id"], ["id"])
        if "platform_id" not in profile_columns:
            batch.add_column(sa.Column("platform_id", sa.Integer(), nullable=True))
            batch.create_index("ix_tge_profiles_platform_id", ["platform_id"], unique=False)
            batch.create_foreign_key("fk_tge_profiles_platform_id_platforms", "platforms", ["platform_id"], ["id"])
        if "tge_environment_id" not in profile_columns:
            batch.add_column(sa.Column("tge_environment_id", sa.String(length=120), nullable=True))
            batch.create_index("ix_tge_profiles_tge_environment_id", ["tge_environment_id"], unique=False)
        if "profile_name" not in profile_columns:
            batch.add_column(sa.Column("profile_name", sa.String(length=120), nullable=True))
        if "proxy_region" not in profile_columns:
            batch.add_column(sa.Column("proxy_region", sa.String(length=80), nullable=True))
        if "proxy_type" not in profile_columns:
            batch.add_column(sa.Column("proxy_type", sa.String(length=80), nullable=True))
        if "last_seen_at" not in profile_columns:
            batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        if "remark" not in profile_columns:
            batch.add_column(sa.Column("remark", sa.Text(), nullable=True))

    if "account_limits" not in tables:
        op.create_table(
            "account_limits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("browse_daily_limit", sa.Integer(), nullable=False),
            sa.Column("like_daily_limit", sa.Integer(), nullable=False),
            sa.Column("bookmark_daily_limit", sa.Integer(), nullable=False),
            sa.Column("visit_profile_daily_limit", sa.Integer(), nullable=False),
            sa.Column("reply_daily_limit", sa.Integer(), nullable=False),
            sa.Column("dm_daily_limit", sa.Integer(), nullable=False),
            sa.Column("follow_daily_limit", sa.Integer(), nullable=False),
            sa.Column("current_browse_count", sa.Integer(), nullable=False),
            sa.Column("current_like_count", sa.Integer(), nullable=False),
            sa.Column("current_bookmark_count", sa.Integer(), nullable=False),
            sa.Column("current_visit_profile_count", sa.Integer(), nullable=False),
            sa.Column("current_reply_count", sa.Integer(), nullable=False),
            sa.Column("current_dm_count", sa.Integer(), nullable=False),
            sa.Column("current_follow_count", sa.Integer(), nullable=False),
            sa.Column("reset_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("account_id"),
        )
        op.create_index("ix_account_limits_account_id", "account_limits", ["account_id"], unique=True)

    if "account_working_windows" not in tables:
        op.create_table(
            "account_working_windows",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("day_of_week", sa.String(length=10), nullable=False),
            sa.Column("start_time", sa.String(length=5), nullable=False),
            sa.Column("end_time", sa.String(length=5), nullable=False),
            sa.Column("timezone", sa.String(length=80), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_account_working_windows_account_id", "account_working_windows", ["account_id"])
        op.create_index("ix_account_working_windows_day_of_week", "account_working_windows", ["day_of_week"])
        op.create_index("ix_account_working_windows_enabled", "account_working_windows", ["enabled"])


def downgrade() -> None:
    op.drop_table("account_working_windows")
    op.drop_table("account_limits")
