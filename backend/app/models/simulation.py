import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    random_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    current_tick: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_ticks: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    ensemble_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    ensemble_seed_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forked_from_tick_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Tick(Base):
    __tablename__ = "ticks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    tick_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    active_agent_ids: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=text("'{}'")
    )
    events: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    world_state_delta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    kpi_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    interventions_applied: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=text("'{}'")
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gemini_calls: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    gemini_tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
