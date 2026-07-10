"""Add browser runtime sessions and tabs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_missing(table: str, column: str, unique: bool = False) -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes(table)}
    name = f"ix_{table}_{column}"
    if name not in indexes:
        op.create_index(name, table, [column], unique=unique)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "browser_sessions" not in tables:
        op.create_table(
            "browser_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("browser_type", sa.String(length=60), nullable=False, server_default="mock"),
            sa.Column("worker_id", sa.Integer(), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=True),
            sa.Column("profile_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="RUNNING"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["profile_id"], ["tge_profiles.id"]),
            sa.ForeignKeyConstraint(["worker_id"], ["worker_nodes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "browser_type", "worker_id", "account_id", "profile_id", "status", "started_at", "last_heartbeat"]:
            _create_index_if_missing("browser_sessions", column, unique=column == "uuid")

    if "browser_tabs" not in tables:
        op.create_table(
            "browser_tabs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("url", sa.String(length=1000), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="OPEN"),
            sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.ForeignKeyConstraint(["session_id"], ["browser_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["uuid", "session_id", "status", "opened_at"]:
            _create_index_if_missing("browser_tabs", column, unique=column == "uuid")


def downgrade() -> None:
    op.drop_table("browser_tabs")
    op.drop_table("browser_sessions")
