import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    name: str
    role: str | None
    faction: str | None
    personality: dict
    goals: list
    resources: dict
    status: str
    is_chat_enabled: bool
    activation_score: float
    working_memory: dict | None
    episodic_memory: list | None
    semantic_memory: dict | None
    created_at: datetime


class AgentChatRequest(BaseModel):
    message: str
    include_memory: bool = True


class AgentChatResponse(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    message: str
    reasoning: str | None = None
