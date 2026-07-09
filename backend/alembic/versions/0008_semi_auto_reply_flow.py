"""Add semi-auto reply preparation flow.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    account_columns = {column["name"] for column in inspector.get_columns("accounts")}
    replay_columns = {column["name"] for column in inspector.get_columns("replay_files")}
    if "last_active_at" not in account_columns:
        op.add_column("accounts", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))
    if "before_fill_screenshot_path" not in replay_columns:
        op.add_column("replay_files", sa.Column("before_fill_screenshot_path", sa.String(length=1000), nullable=True))
    if "after_fill_screenshot_path" not in replay_columns:
        op.add_column("replay_files", sa.Column("after_fill_screenshot_path", sa.String(length=1000), nullable=True))
    if "timeline_path" not in replay_columns:
        op.add_column("replay_files", sa.Column("timeline_path", sa.String(length=1000), nullable=True))
    if "platform_selectors" not in tables:
        op.create_table(
            "platform_selectors",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=False),
            sa.Column("selector_key", sa.String(length=120), nullable=False),
            sa.Column("selector_value", sa.String(length=1000), nullable=False),
            sa.Column("selector_type", sa.String(length=40), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("platform", "selector_key", "selector_value", name="uq_platform_selector_value"),
        )
        op.create_index(op.f("ix_platform_selectors_enabled"), "platform_selectors", ["enabled"], unique=False)
        op.create_index(op.f("ix_platform_selectors_platform"), "platform_selectors", ["platform"], unique=False)
        op.create_index(op.f("ix_platform_selectors_selector_key"), "platform_selectors", ["selector_key"], unique=False)
        op.create_index(op.f("ix_platform_selectors_status"), "platform_selectors", ["status"], unique=False)
        op.create_index(op.f("ix_platform_selectors_uuid"), "platform_selectors", ["uuid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_platform_selectors_uuid"), table_name="platform_selectors")
    op.drop_index(op.f("ix_platform_selectors_status"), table_name="platform_selectors")
    op.drop_index(op.f("ix_platform_selectors_selector_key"), table_name="platform_selectors")
    op.drop_index(op.f("ix_platform_selectors_platform"), table_name="platform_selectors")
    op.drop_index(op.f("ix_platform_selectors_enabled"), table_name="platform_selectors")
    op.drop_table("platform_selectors")
    op.drop_column("replay_files", "timeline_path")
    op.drop_column("replay_files", "after_fill_screenshot_path")
    op.drop_column("replay_files", "before_fill_screenshot_path")
    op.drop_column("accounts", "last_active_at")
