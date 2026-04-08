import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IngestionSource(Base):
    __tablename__ = "ingestion_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class IngestedEvent(Base):
    __tablename__ = "ingested_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    ingestion_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_sources.id", ondelete="CASCADE"), nullable=False
    )
    simulation_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed_intervention: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    intervention_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    target_agent_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    response_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    responses: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    aggregate_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
