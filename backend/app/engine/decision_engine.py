"""
Decision engine: resolve LLM decisions for activated agents using Gemini function calling.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.gemini.client import GeminiClient
from app.gemini.decisions import get_agent_decision
from app.models.agent import Agent

logger = logging.getLogger(__name__)

MAX_CONCURRENT_GEMINI = 5  # Semaphore limit to prevent API flooding


@dataclass
class AgentDecision:
    agent_id: str
    agent_name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


async def get_decisions(
    active_agents: list[Agent],
    world_state: dict[str, Any],
    tick_number: int,
    episodic_memories: dict[str, list[dict]] | None = None,
    client: GeminiClient | None = None,
) -> list[AgentDecision]:
    """
    Get Gemini decisions for all activated agents concurrently.
    Bounded by semaphore of MAX_CONCURRENT_GEMINI to avoid flooding the API.
    Falls back to do_nothing on any failure.
    """
    gemini = client or GeminiClient()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_GEMINI)

    async def resolve_one(agent: Agent) -> AgentDecision:
        async with semaphore:
            try:
                memories = episodic_memories or {}
                agent_memories = memories.get(str(agent.id), [])
                memories_text = _format_memories(agent_memories[:5])

                action = await get_agent_decision(
                    agent_name=agent.name,
                    agent_role=agent.role or "unknown",
                    agent_faction=agent.faction or "none",
                    personality=agent.personality if isinstance(agent.personality, dict) else {},
                    goals=agent.goals if isinstance(agent.goals, list) else [],
                    resources=agent.resources if isinstance(agent.resources, dict) else {},
                    tick_number=tick_number,
                    world_state_summary=_format_world_state(world_state),
                    recent_events=_format_recent_events(world_state),
                    episodic_memories=memories_text,
                    recent_interactions="",
                    client=gemini,
                )
                return AgentDecision(
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    action=action.action_name,
                    params=action.parameters,
                    reasoning=action.reasoning,
                )

            except Exception as exc:
                logger.error("Decision failed for agent %s: %s", agent.name, exc)
                return AgentDecision(
                    agent_id=str(agent.id),
                    agent_name=agent.name,
                    action="do_nothing",
                    params={"reasoning": f"Error: {exc}"},
                )

    tasks = [resolve_one(agent) for agent in active_agents]
    decisions = await asyncio.gather(*tasks)
    logger.info(
        "Decisions resolved: %d active agents at tick %d",
        len(decisions),
        tick_number,
    )
    return list(decisions)


def _format_world_state(world_state: dict[str, Any]) -> str:
    summary = world_state.get("summary", "No summary available")
    kpis = world_state.get("kpi_values", {})
    kpi_str = ", ".join(f"{k}={v:.1f}" for k, v in kpis.items()) if kpis else "none"
    return f"{summary}\nCurrent KPIs: {kpi_str}"


def _format_recent_events(world_state: dict[str, Any]) -> str:
    events = world_state.get("recent_events", [])
    if not events:
        return "No recent events."
    lines = []
    for e in events[-5:]:
        if isinstance(e, dict):
            lines.append(f"- {e.get('description', str(e))}")
    return "\n".join(lines) or "No recent events."


def _format_memories(memories: list[dict]) -> str:
    if not memories:
        return "No relevant memories."
    lines = []
    for m in memories:
        if isinstance(m, dict):
            tick = m.get("tick", "?")
            summary = m.get("summary", "")
            lines.append(f"[Tick {tick}] {summary}")
    return "\n".join(lines) or "No relevant memories."
