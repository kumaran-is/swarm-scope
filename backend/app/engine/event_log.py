"""
Append-only event log. Events are stored in ticks.events JSONB.
Never mutate past tick records.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import Tick

logger = logging.getLogger(__name__)

EVENT_TYPES = [
    "agent_action",
    "rule_outcome",
    "intervention_applied",
    "kpi_change",
    "memory_compressed",
    "gemini_call",
    "error",
]


def make_event(
    event_type: str,
    agent_id: str | None,
    data: dict[str, Any],
    tick: int,
) -> dict[str, Any]:
    """Create a single event record."""
    if event_type not in EVENT_TYPES:
        logger.warning("Unknown event type: %s", event_type)
    return {
        "type": event_type,
        "agent_id": agent_id,
        "tick": tick,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "data": data,
    }


async def save_tick(
    simulation_run_id: UUID,
    tick_number: int,
    phase: str,
    active_agent_ids: list[str],
    events: list[dict[str, Any]],
    world_state_delta: dict[str, Any],
    kpi_values: dict[str, float],
    snapshot: dict[str, Any],
    interventions_applied: list[str],
    duration_ms: int,
    gemini_calls: int,
    gemini_tokens_used: int,
    db: AsyncSession,
) -> Tick:
    """
    Persist a completed tick to the database. Immutable after creation.
    """
    import uuid

    tick = Tick(
        simulation_run_id=simulation_run_id,
        tick_number=tick_number,
        phase=phase,
        active_agent_ids=[uuid.UUID(aid) for aid in active_agent_ids if _is_valid_uuid(aid)],
        events=events,
        world_state_delta=world_state_delta,
        kpi_values=kpi_values,
        snapshot=snapshot,
        interventions_applied=[uuid.UUID(iid) for iid in interventions_applied if _is_valid_uuid(iid)],
        duration_ms=duration_ms,
        gemini_calls=gemini_calls,
        gemini_tokens_used=gemini_tokens_used,
    )
    db.add(tick)
    await db.commit()
    await db.refresh(tick)
    logger.info(
        "Tick %d saved: %d events, %d gemini_calls, %dms",
        tick_number,
        len(events),
        gemini_calls,
        duration_ms,
    )
    return tick


def _is_valid_uuid(value: str) -> bool:
    import uuid as _uuid
    try:
        _uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False
