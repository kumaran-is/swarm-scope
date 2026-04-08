import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, server_default="general")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="draft")
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
