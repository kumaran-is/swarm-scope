import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    influence_graph: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    key_findings: Mapped[list] = mapped_column(JSONB, nullable=True, server_default=text("'[]'"))
    kpi_trajectories: Mapped[dict] = mapped_column(JSONB, nullable=True, server_default=text("'{}'"))
    tool_usage_log: Mapped[list] = mapped_column(JSONB, nullable=True, server_default=text("'[]'"))
    counterfactual_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class InfluenceEdge(Base):
    __tablename__ = "influence_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    target_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str | None] = mapped_column(nullable=True)
    tick_number: Mapped[int | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    context: Mapped[str | None] = mapped_column(nullable=True)
