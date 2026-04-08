import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    faction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    personality: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    goals: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    resources: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="idle")
    is_chat_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    activation_score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0.0")
    working_memory: Mapped[dict] = mapped_column(JSONB, nullable=True, server_default=text("'{}'"))
    episodic_memory: Mapped[list] = mapped_column(JSONB, nullable=True, server_default=text("'[]'"))
    semantic_memory: Mapped[dict] = mapped_column(JSONB, nullable=True, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
