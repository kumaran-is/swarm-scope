import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SimulationCreate(BaseModel):
    scenario_id: uuid.UUID
    random_seed: int | None = None
    max_ticks: int = 15
    config: dict = {}


class SimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    random_seed: int
    status: str
    current_tick: int
    max_ticks: int
    config: dict
    ensemble_run_id: uuid.UUID | None = None
    ensemble_seed_index: int | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TickResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_run_id: uuid.UUID
    tick_number: int
    phase: str
    active_agent_ids: list
    events: list
    world_state_delta: dict | None
    kpi_values: dict | None
    snapshot: dict | None
    interventions_applied: list
    duration_ms: int | None
    gemini_calls: int
    gemini_tokens_used: int
    created_at: datetime
