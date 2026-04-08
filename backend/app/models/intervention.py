import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_at_tick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
