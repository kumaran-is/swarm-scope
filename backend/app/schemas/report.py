import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_run_id: uuid.UUID
    executive_summary: str | None
    narrative: str | None
    timeline: list
    influence_graph: dict
    key_findings: list | None
    kpi_trajectories: dict | None
    counterfactual_notes: str | None
    created_at: datetime


class ReportGenerateRequest(BaseModel):
    include_counterfactuals: bool = True
    include_influence_graph: bool = True
