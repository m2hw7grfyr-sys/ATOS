"""Add AI provider pipeline storage.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "llm_providers" not in tables:
        op.create_table(
            "llm_providers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("provider_name", sa.String(length=120), nullable=False),
            sa.Column("provider_type", sa.String(length=40), nullable=False),
            sa.Column("api_base_url", sa.String(length=500), nullable=True),
            sa.Column("api_key", sa.Text(), nullable=True),
            sa.Column("model_name", sa.String(length=160), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("use_for_analysis", sa.Boolean(), nullable=False),
            sa.Column("use_for_reply", sa.Boolean(), nullable=False),
            sa.Column("use_for_embedding", sa.Boolean(), nullable=False),
            sa.Column("is_mock", sa.Boolean(), nullable=False),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False),
            sa.Column("max_retries", sa.Integer(), nullable=False),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_llm_providers_uuid", "llm_providers", ["uuid"], unique=True)
        op.create_index("ix_llm_providers_provider_type", "llm_providers", ["provider_type"])
        op.create_index("ix_llm_providers_enabled", "llm_providers", ["enabled"])
        op.create_index("ix_llm_providers_priority", "llm_providers", ["priority"])
        op.create_index("ix_llm_providers_is_mock", "llm_providers", ["is_mock"])
        op.create_index("ix_llm_providers_status", "llm_providers", ["status"])

    if "ai_analysis_results" not in tables:
        op.create_table(
            "ai_analysis_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("ai_task_id", sa.Integer(), nullable=True),
            sa.Column("intent", sa.String(length=120), nullable=True),
            sa.Column("pain_point", sa.Text(), nullable=True),
            sa.Column("commercial_score", sa.Integer(), nullable=False),
            sa.Column("risk_score", sa.Integer(), nullable=False),
            sa.Column("recommended_strategy", sa.String(length=120), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("provider_used", sa.String(length=120), nullable=False),
            sa.Column("model_used", sa.String(length=160), nullable=False),
            sa.Column("generation_source", sa.String(length=40), nullable=False),
            sa.Column("raw_result", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["ai_task_id"], ["ai_tasks.id"]),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_analysis_results_uuid", "ai_analysis_results", ["uuid"], unique=True)
        op.create_index("ix_ai_analysis_results_post_id", "ai_analysis_results", ["post_id"])
        op.create_index("ix_ai_analysis_results_ai_task_id", "ai_analysis_results", ["ai_task_id"])
        op.create_index("ix_ai_analysis_results_generation_source", "ai_analysis_results", ["generation_source"])

    if "prompt_templates" not in tables:
        op.create_table(
            "prompt_templates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("template_type", sa.String(length=40), nullable=False),
            sa.Column("platform", sa.String(length=80), nullable=True),
            sa.Column("strategy", sa.String(length=80), nullable=True),
            sa.Column("tone", sa.String(length=80), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("version", sa.String(length=40), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_prompt_templates_uuid", "prompt_templates", ["uuid"], unique=True)
        op.create_index("ix_prompt_templates_template_type", "prompt_templates", ["template_type"])
        op.create_index("ix_prompt_templates_platform", "prompt_templates", ["platform"])
        op.create_index("ix_prompt_templates_strategy", "prompt_templates", ["strategy"])
        op.create_index("ix_prompt_templates_tone", "prompt_templates", ["tone"])
        op.create_index("ix_prompt_templates_enabled", "prompt_templates", ["enabled"])
        op.create_index("ix_prompt_templates_status", "prompt_templates", ["status"])

    if "ai_generation_logs" not in tables:
        op.create_table(
            "ai_generation_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("uuid", sa.String(length=36), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=True),
            sa.Column("ai_task_id", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=120), nullable=False),
            sa.Column("model", sa.String(length=160), nullable=False),
            sa.Column("prompt_version", sa.String(length=40), nullable=False),
            sa.Column("purpose", sa.String(length=40), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=False),
            sa.Column("token_estimate", sa.Integer(), nullable=False),
            sa.Column("generation_source", sa.String(length=40), nullable=False),
            sa.Column("fallback_used", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["ai_task_id"], ["ai_tasks.id"]),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_generation_logs_uuid", "ai_generation_logs", ["uuid"], unique=True)
        op.create_index("ix_ai_generation_logs_post_id", "ai_generation_logs", ["post_id"])
        op.create_index("ix_ai_generation_logs_ai_task_id", "ai_generation_logs", ["ai_task_id"])
        op.create_index("ix_ai_generation_logs_provider", "ai_generation_logs", ["provider"])
        op.create_index("ix_ai_generation_logs_purpose", "ai_generation_logs", ["purpose"])
        op.create_index("ix_ai_generation_logs_generation_source", "ai_generation_logs", ["generation_source"])
        op.create_index("ix_ai_generation_logs_status", "ai_generation_logs", ["status"])


def downgrade() -> None:
    op.drop_table("ai_generation_logs")
    op.drop_table("prompt_templates")
    op.drop_table("ai_analysis_results")
    op.drop_table("llm_providers")
