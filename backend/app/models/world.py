import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorldModel(Base):
    __tablename__ = "world_models"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    entities: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    factions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    resources: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    constraints: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    tensions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    kpis: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    raw_extraction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
