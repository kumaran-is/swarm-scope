"""
Three-layer memory manager: working / episodic / semantic.
"""

import logging

from app.engine.decision_engine import AgentDecision
from app.engine.rule_engine import RuleOutcome
from app.gemini.client import GeminiClient
from app.gemini.prompts import MEMORY_COMPRESSION_PROMPT
from app.models.agent import Agent

logger = logging.getLogger(__name__)

MAX_EPISODIC_ENTRIES = 20
COMPRESS_THRESHOLD = 20


def update_working_memory(
    agent: Agent,
    tick_events: list[AgentDecision | RuleOutcome],
    tick_number: int,
) -> None:
    """Set current tick context in working memory. Clears previous tick's context."""
    events_summary = []
    for event in tick_events:
        if isinstance(event, AgentDecision) and event.agent_id == str(agent.id):
            events_summary.append(
                {"type": "decision", "action": event.action, "params": event.params}
            )
        elif isinstance(event, RuleOutcome):
            events_summary.append(
                {"type": "rule", "rule_type": event.rule_type, "desc": event.description}
            )

    agent.working_memory = {
        "tick": tick_number,
        "events_this_tick": events_summary,
        "active_goals": (agent.goals[:3] if isinstance(agent.goals, list) else []),
    }


def add_episodic_memory(
    agent: Agent,
    tick: int,
    event_summary: str,
    emotional_valence: float = 0.0,
    importance_score: float = 0.5,
) -> None:
    """Append a new episodic memory entry. Does not exceed MAX_EPISODIC_ENTRIES."""
    episodic = list(agent.episodic_memory or [])
    entry = {
        "tick": tick,
        "summary": event_summary,
        "emotional_valence": emotional_valence,
        "importance_score": importance_score,
        "embedding": None,  # computed on demand
    }
    episodic.append(entry)
    # Keep most recent + highest importance if over limit
    if len(episodic) > MAX_EPISODIC_ENTRIES:
        episodic.sort(key=lambda e: (e.get("importance_score", 0.5), e.get("tick", 0)), reverse=True)
        episodic = episodic[:MAX_EPISODIC_ENTRIES]
    agent.episodic_memory = episodic


async def compress_memories(
    agent: Agent,
    client: GeminiClient | None = None,
) -> bool:
    """
    If episodic memory exceeds threshold, compress the 5 least-important entries
    into semantic memory via Gemini and remove them from episodic.
    Returns True if compression occurred.
    """
    episodic = list(agent.episodic_memory or [])
    if len(episodic) < COMPRESS_THRESHOLD:
        return False

    gemini = client or GeminiClient()

    # Find 5 least important entries (by importance_score + recency)
    sorted_by_importance = sorted(
        episodic, key=lambda e: (e.get("importance_score", 0.5), e.get("tick", 0))
    )
    to_compress = sorted_by_importance[:5]
    to_keep = sorted_by_importance[5:]

    # Format for compression prompt
    entries_text = "\n".join(
        f"[Tick {e.get('tick', '?')}] {e.get('summary', '')}" for e in to_compress
    )
    ticks = sorted(e.get("tick", 0) for e in to_compress)
    tick_start = ticks[0] if ticks else "?"
    tick_end = ticks[-1] if ticks else "?"

    prompt = MEMORY_COMPRESSION_PROMPT.format(
        agent_name=agent.name,
        agent_role=agent.role or "unknown",
        tick_start=tick_start,
        tick_end=tick_end,
        episodic_entries=entries_text,
    )

    try:
        response = await gemini.extract_structured(
            prompt=prompt,
            response_schema=str,
            purpose=f"memory_compression:{agent.name}",
        )
        compressed_text = response.text.strip('"').strip()

        # Merge into semantic memory
        semantic = dict(agent.semantic_memory or {})
        compressed_list = semantic.get("compressed_episodes", [])
        compressed_list.append({"ticks": f"{tick_start}-{tick_end}", "summary": compressed_text})
        semantic["compressed_episodes"] = compressed_list
        agent.semantic_memory = semantic
        agent.episodic_memory = to_keep

        logger.info(
            "Memory compressed for %s: %d episodes → 1 semantic entry",
            agent.name,
            len(to_compress),
        )
        return True

    except Exception as exc:
        logger.error("Memory compression failed for %s: %s", agent.name, exc)
        return False


async def compress_if_needed(
    agents: list[Agent],
    client: GeminiClient | None = None,
) -> None:
    """Compress memories for all agents that have exceeded the threshold."""
    for agent in agents:
        episodic = agent.episodic_memory or []
        if len(episodic) >= COMPRESS_THRESHOLD:
            await compress_memories(agent, client=client)
