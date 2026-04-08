import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorldModelUpdate(BaseModel):
    summary: str | None = None
    entities: list | None = None
    factions: list | None = None
    resources: list | None = None
    constraints: list | None = None
    tensions: list | None = None
    kpis: list | None = None


class WorldModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    summary: str | None
    entities: list
    factions: list
    resources: list
    constraints: list
    tensions: list
    kpis: list
    raw_extraction: dict | None
    created_at: datetime
    updated_at: datetime
