"""
Selective activation: score each agent to decide who invokes Gemini this tick.

Cost-control mechanism — only top K agents make LLM calls per tick.
"""

import logging
import random
from typing import Any

from app.models.agent import Agent

logger = logging.getLogger(__name__)


def compute_activation_scores(
    agents: list[Agent],
    world_state: dict[str, Any],
    current_tick: int,
    last_activated: dict[str, int],  # agent_id -> last tick activated
    random_gen: random.Random | None = None,
    top_k: int = 15,
) -> list[tuple[Agent, float]]:
    """
    Score each agent 0.0-1.0 based on multiple factors.
    Returns sorted list (highest score first). Caller takes top K.

    Scoring weights:
    - relevance (0.30): is agent's domain affected by recent events?
    - tension (0.25): is agent in a high-conflict situation?
    - goal_proximity (0.25): is agent close to achieving/failing a goal?
    - recency (0.15): how long since agent was last activated?
    - random_jitter (0.05): seeded random for variety
    """
    if random_gen is None:
        random_gen = random.Random(current_tick)

    recent_events = world_state.get("recent_events", [])
    active_factions = {e.get("faction", "") for e in recent_events if isinstance(e, dict)}
    world_tensions = world_state.get("tensions", [])

    scored: list[tuple[Agent, float]] = []

    for agent in agents:
        if agent.status in ("eliminated",):
            # Eliminated agents never activate
            scored.append((agent, 0.0))
            continue

        # 1. Relevance: agent's faction appears in recent events
        agent_faction = agent.faction or ""
        relevance = 1.0 if agent_faction in active_factions else 0.3
        relevance = min(1.0, relevance)

        # 2. Tension: agent is involved in a known tension
        tension_score = 0.0
        for tension in world_tensions:
            between = tension.get("between", []) if isinstance(tension, dict) else []
            if agent.name in between or agent_faction in between:
                intensity = tension.get("intensity", 5) if isinstance(tension, dict) else 5
                tension_score = max(tension_score, min(1.0, intensity / 10.0))
        tension_score = max(0.2, tension_score)

        # 3. Goal proximity: score by how achievable current goals appear
        goals = agent.goals if isinstance(agent.goals, list) else []
        goal_proximity = 0.5  # neutral default
        if goals:
            # High-priority goals drive higher activation
            priorities = [g.get("priority", 5) if isinstance(g, dict) else 5 for g in goals]
            min_priority = min(priorities) if priorities else 5
            goal_proximity = max(0.2, 1.0 - (min_priority - 1) / 10.0)

        # 4. Recency: longer gap since last activation → higher score
        last_tick = last_activated.get(str(agent.id), 0)
        ticks_since = current_tick - last_tick
        recency = min(1.0, ticks_since / 5.0)  # fully recharged after 5 ticks

        # 5. Random jitter (seeded for reproducibility)
        jitter = random_gen.uniform(0.0, 1.0)

        # Weighted sum
        score = (
            0.30 * relevance
            + 0.25 * tension_score
            + 0.25 * goal_proximity
            + 0.15 * recency
            + 0.05 * jitter
        )

        # Dormant agents get a penalty
        if agent.status == "dormant":
            score *= 0.5

        scored.append((agent, round(score, 4)))

    scored.sort(key=lambda x: x[1], reverse=True)

    logger.debug(
        "Activation scores computed: %d agents, top K=%d, tick=%d",
        len(scored),
        top_k,
        current_tick,
    )
    return scored
