"""
Structured extraction from source documents using Gemini.
"""

import json
import logging

from pydantic import BaseModel

from app.gemini.client import GeminiClient
from app.gemini.prompts import AGENT_GENERATION_PROMPT, WORLD_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


# ── Pydantic schemas for structured output ──────────────────────────────────


class EntitySchema(BaseModel):
    name: str
    type: str
    description: str
    attributes: list[str] = []


class FactionSchema(BaseModel):
    name: str
    goals: list[str]
    resources: list[str]
    relationships: list[str] = []


class ResourceSchema(BaseModel):
    name: str
    type: str
    quantity: str
    controlled_by: str = ""


class ConstraintSchema(BaseModel):
    description: str
    type: str
    severity: str


class TensionSchema(BaseModel):
    between: list[str]
    description: str
    intensity: int


class KPISchema(BaseModel):
    name: str
    description: str
    unit: str
    initial_value: float
    target: float


class WorldExtraction(BaseModel):
    summary: str
    entities: list[EntitySchema]
    factions: list[FactionSchema]
    resources: list[ResourceSchema]
    constraints: list[ConstraintSchema]
    tensions: list[TensionSchema]
    kpis: list[KPISchema]


class AgentPersonality(BaseModel):
    openness: int
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int
    decision_style: str
    risk_tolerance: int


class AgentGoal(BaseModel):
    description: str
    priority: int
    measurable_outcome: str = ""


class AgentResources(BaseModel):
    influence: int
    capital: int
    information: int
    alliances: int


class AgentProfile(BaseModel):
    name: str
    role: str
    faction: str
    personality: AgentPersonality
    goals: list[AgentGoal]
    resources: AgentResources
    background: str = ""


class AgentPopulation(BaseModel):
    agents: list[AgentProfile]


# ── Extraction functions ────────────────────────────────────────────────────


async def extract_world_model(
    source_text: str,
    client: GeminiClient | None = None,
) -> WorldExtraction:
    """
    Extract structured world model from source document text.
    Retries once on JSON parse failure, returning partial result on second failure.
    """
    gemini = client or GeminiClient()
    prompt = WORLD_EXTRACTION_PROMPT + source_text

    for attempt in range(2):
        try:
            response = await gemini.extract_structured(
                prompt=prompt,
                response_schema=WorldExtraction,
                purpose="world_extraction",
            )
            # google-genai returns parsed JSON in response.text when schema is provided
            raw_text = response.text
            data = json.loads(raw_text)
            extraction = WorldExtraction.model_validate(data)
            logger.info(
                "World extraction complete: %d entities, %d factions, %d KPIs",
                len(extraction.entities),
                len(extraction.factions),
                len(extraction.kpis),
            )
            return extraction

        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 0:
                logger.warning("World extraction JSON parse failed, retrying: %s", exc)
                continue
            logger.error("World extraction failed after retry, returning minimal result: %s", exc)
            return WorldExtraction(
                summary="Extraction failed — manual review required.",
                entities=[],
                factions=[],
                resources=[],
                constraints=[],
                tensions=[],
                kpis=[],
            )
    # unreachable but satisfies type checker
    raise RuntimeError("Extraction failed")


async def generate_agents(
    world_model: WorldExtraction,
    count: int = 10,
    client: GeminiClient | None = None,
) -> list[AgentProfile]:
    """
    Generate agent population from world model.
    Retries once on JSON parse failure.
    """
    gemini = client or GeminiClient()
    import json as _json

    world_model_json = _json.dumps(world_model.model_dump(), indent=2)
    prompt = AGENT_GENERATION_PROMPT.format(
        count=count,
        world_model_json=world_model_json,
    )

    for attempt in range(2):
        try:
            response = await gemini.extract_structured(
                prompt=prompt,
                response_schema=AgentPopulation,
                purpose="agent_generation",
            )
            raw_text = response.text
            data = _json.loads(raw_text)
            population = AgentPopulation.model_validate(data)
            logger.info(
                "Agent generation complete: %d agents generated (requested %d)",
                len(population.agents),
                count,
            )
            return population.agents

        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 0:
                logger.warning("Agent generation JSON parse failed, retrying: %s", exc)
                continue
            logger.error("Agent generation failed after retry, returning empty list: %s", exc)
            return []
    return []
