"""Agent population and chat endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.gemini.client import GeminiClient
from app.gemini.prompts import AGENT_CHAT_PROMPT
from app.models.agent import Agent
from app.models.simulation import SimulationRun
from app.models.world import WorldModel
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agents"])


@router.get("/simulations/{sim_id}/agents", response_model=list[AgentResponse])
async def list_agents(sim_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await _get_run_or_404(sim_id, db)
    result = await db.execute(
        select(Agent).where(Agent.scenario_id == run.scenario_id)
    )
    return list(result.scalars().all())


@router.get("/simulations/{sim_id}/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(sim_id: uuid.UUID, agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("/simulations/{sim_id}/agents/{agent_id}/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    sim_id: uuid.UUID,
    agent_id: uuid.UUID,
    request: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Chat with a chat-enabled agent in character using Gemini."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.is_chat_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This agent is not chat-enabled",
        )

    run = await _get_run_or_404(sim_id, db)

    # Get world summary
    world_result = await db.execute(
        select(WorldModel).where(WorldModel.scenario_id == run.scenario_id)
    )
    world = world_result.scalars().first()
    world_summary = world.summary if world else "Unknown scenario"

    personality = agent.personality or {}
    resources = agent.resources or {}
    goals = agent.goals or []

    personality_summary = (
        f"decision_style={personality.get('decision_style', 'rational')}, "
        f"risk_tolerance={personality.get('risk_tolerance', 5)}"
    )
    goals_summary = "; ".join(
        g.get("description", "") for g in goals[:2] if isinstance(g, dict)
    )

    # Build relevant memories text
    episodic = agent.episodic_memory or []
    memories_text = "\n".join(
        f"[Tick {m.get('tick', '?')}] {m.get('summary', '')}"
        for m in episodic[-5:]
        if isinstance(m, dict)
    ) or "No memories yet."

    prompt = AGENT_CHAT_PROMPT.format(
        agent_name=agent.name,
        agent_role=agent.role or "unknown",
        scenario_name="SwarmScope Simulation",
        faction=agent.faction or "none",
        personality_summary=personality_summary,
        goals_summary=goals_summary,
        influence=resources.get("influence", 50),
        capital=resources.get("capital", 50),
        information=resources.get("information", 50),
        status=agent.status,
        current_tick=run.current_tick,
        world_state_summary=world_summary,
        relevant_memories=memories_text,
        recent_actions="",
        user_message=request.message,
    )

    gemini = GeminiClient()
    try:
        response = await gemini.extract_structured(
            prompt=prompt,
            response_schema=str,
            purpose=f"agent_chat:{agent.name}",
        )
        reply = str(response.text).strip('"').strip()
    except Exception as exc:
        logger.error("Agent chat failed for %s: %s", agent.name, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat service unavailable: {exc}",
        ) from exc

    return AgentChatResponse(
        agent_id=agent.id,
        agent_name=agent.name,
        message=reply,
    )


async def _get_run_or_404(sim_id: uuid.UUID, db: AsyncSession) -> SimulationRun:
    result = await db.execute(select(SimulationRun).where(SimulationRun.id == sim_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return run
