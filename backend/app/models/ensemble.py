import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EnsembleRun(Base):
    __tablename__ = "ensemble_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    ensemble_size: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    base_config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    statistics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
