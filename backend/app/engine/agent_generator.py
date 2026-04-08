"""
Agent generator: converts a WorldModel into a population of Agent ORM records.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini.client import GeminiClient
from app.gemini.extraction import WorldExtraction
from app.gemini.extraction import generate_agents as gemini_generate
from app.models.agent import Agent
from app.models.world import WorldModel

logger = logging.getLogger(__name__)


async def generate_agents(
    world_model: WorldModel,
    scenario_id: UUID,
    count: int = 10,
    db: AsyncSession | None = None,
    client: GeminiClient | None = None,
) -> list[Agent]:
    """
    Generate `count` agents from a compiled WorldModel using Gemini.
    - Top 10 agents by influence get is_chat_enabled=True.
    - All memory layers initialized to empty.
    - Persists agents to the agents table if db is provided.
    """
    # Reconstruct the WorldExtraction from the ORM model for Gemini
    world_extraction = WorldExtraction(
        summary=world_model.summary or "",
        entities=world_model.entities,
        factions=world_model.factions,
        resources=world_model.resources,
        constraints=world_model.constraints,
        tensions=world_model.tensions,
        kpis=world_model.kpis,
    )

    profiles = await gemini_generate(world_extraction, count=count, client=client)

    if not profiles:
        logger.error("No agent profiles returned from Gemini — cannot generate agents")
        return []

    # Sort by influence descending to mark top 10 as chat-enabled
    profiles_sorted = sorted(
        profiles, key=lambda p: p.resources.influence, reverse=True
    )
    chat_enabled_ids = set(range(min(10, len(profiles_sorted))))

    agents: list[Agent] = []
    for idx, profile in enumerate(profiles_sorted):
        agent = Agent(
            scenario_id=scenario_id,
            name=profile.name,
            role=profile.role,
            faction=profile.faction,
            personality=profile.personality.model_dump(),
            goals=[g.model_dump() for g in profile.goals],
            resources=profile.resources.model_dump(),
            status="idle",
            is_chat_enabled=(idx in chat_enabled_ids),
            activation_score=0.0,
            working_memory={},
            episodic_memory=[],
            semantic_memory={},
        )
        agents.append(agent)

    if db is not None:
        for agent in agents:
            db.add(agent)
        await db.commit()
        for agent in agents:
            await db.refresh(agent)

    logger.info(
        "Generated %d agents for scenario %s (chat-enabled: %d)",
        len(agents),
        scenario_id,
        sum(1 for a in agents if a.is_chat_enabled),
    )
    return agents
