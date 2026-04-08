import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    domain: str = "general"
    config: dict = {}


class ScenarioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    config: dict | None = None


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    source_file_path: str | None
    source_text: str | None
    domain: str
    config: dict
    status: str
    user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
