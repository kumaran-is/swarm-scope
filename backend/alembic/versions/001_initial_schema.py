"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2026-04-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # scenarios
    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_file_path", sa.String(500), nullable=True),
        sa.Column("source_text", sa.Text, nullable=True),
        sa.Column("domain", sa.String(100), nullable=False, server_default="general"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # world_models
    op.create_table(
        "world_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("entities", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("factions", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("resources", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("constraints", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("tensions", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("kpis", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("raw_extraction", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # agents
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("faction", sa.String(255), nullable=True),
        sa.Column("personality", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("goals", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("resources", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(50), nullable=False, server_default="idle"),
        sa.Column("is_chat_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("activation_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("working_memory", postgresql.JSONB, nullable=True, server_default=sa.text("'{}'")),
        sa.Column("episodic_memory", postgresql.JSONB, nullable=True, server_default=sa.text("'[]'")),
        sa.Column("semantic_memory", postgresql.JSONB, nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ensemble_runs
    op.create_table(
        "ensemble_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ensemble_size", sa.Integer, nullable=False, server_default="5"),
        sa.Column("base_config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("statistics", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # simulation_runs
    op.create_table(
        "simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("random_seed", sa.BigInteger, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("current_tick", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_ticks", sa.Integer, nullable=False, server_default="15"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("ensemble_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ensemble_seed_index", sa.Integer, nullable=True),
        sa.Column("forked_from_tick_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ticks
    op.create_table(
        "ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tick_number", sa.Integer, nullable=False),
        sa.Column("phase", sa.String(50), nullable=False),
        sa.Column("active_agent_ids", postgresql.ARRAY(postgresql.UUID), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("events", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("world_state_delta", postgresql.JSONB, nullable=True),
        sa.Column("kpi_values", postgresql.JSONB, nullable=True),
        sa.Column("snapshot", postgresql.JSONB, nullable=True),
        sa.Column("interventions_applied", postgresql.ARRAY(postgresql.UUID), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("gemini_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("gemini_tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("simulation_run_id", "tick_number"),
    )

    # interventions
    op.create_table(
        "interventions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("target_tick", sa.Integer, nullable=True),
        sa.Column("applied_at_tick", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # reports
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("narrative", sa.Text, nullable=True),
        sa.Column("timeline", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("influence_graph", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("key_findings", postgresql.JSONB, nullable=True, server_default=sa.text("'[]'")),
        sa.Column("kpi_trajectories", postgresql.JSONB, nullable=True, server_default=sa.text("'{}'")),
        sa.Column("counterfactual_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # influence_edges
    op.create_table(
        "influence_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(100), nullable=True),
        sa.Column("tick_number", sa.Integer, nullable=True),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("context", sa.Text, nullable=True),
    )

    # surveys
    op.create_table(
        "surveys",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("target_agent_ids", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("response_format", sa.String(100), nullable=True),
        sa.Column("responses", postgresql.JSONB, nullable=True),
        sa.Column("aggregate_analysis", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ingestion_sources
    op.create_table(
        "ingestion_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("mapping_rules", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ingested_events
    op.create_table(
        "ingested_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("ingestion_source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingestion_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("processed_intervention", postgresql.JSONB, nullable=True),
        sa.Column("intervention_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("ingested_events")
    op.drop_table("ingestion_sources")
    op.drop_table("surveys")
    op.drop_table("influence_edges")
    op.drop_table("reports")
    op.drop_table("interventions")
    op.drop_table("ticks")
    op.drop_table("simulation_runs")
    op.drop_table("ensemble_runs")
    op.drop_table("agents")
    op.drop_table("world_models")
    op.drop_table("scenarios")
    op.drop_table("users")
