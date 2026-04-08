import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InterventionCreate(BaseModel):
    type: str  # inject_event | modify_agent | modify_world
    payload: dict
    description: str | None = None
    target_tick: int | None = None


class InterventionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_run_id: uuid.UUID
    type: str
    payload: dict
    description: str | None
    target_tick: int | None
    applied_at_tick: int | None
    status: str
    created_at: datetime
