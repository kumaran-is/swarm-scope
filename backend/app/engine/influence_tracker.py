"""
Influence tracker: records agent-to-agent influence edges per tick.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.decision_engine import AgentDecision
from app.engine.state_manager import WorldStateDelta
from app.models.report import InfluenceEdge

logger = logging.getLogger(__name__)


async def record_influence_edges(
    simulation_run_id: UUID,
    tick_number: int,
    decisions: list[AgentDecision],
    delta: WorldStateDelta,
    db: AsyncSession,
) -> list[InfluenceEdge]:
    """
    Extract agent-to-agent influence relationships from decisions and delta,
    and persist them as InfluenceEdge records.
    """
    edges: list[InfluenceEdge] = []

    # Extract edges from relationship changes in the delta
    for change in delta.relationship_changes:
        change_type = change.get("type", "")
        from_id = change.get("from", "")
        to_id = change.get("to", "")
        if not (from_id and to_id):
            continue

        try:
            source_uuid = UUID(from_id)
            target_uuid = UUID(to_id)
        except (ValueError, TypeError):
            logger.debug("Skipping influence edge with invalid UUIDs: %s -> %s", from_id, to_id)
            continue

        weight = _action_type_to_weight(change_type)
        edge = InfluenceEdge(
            simulation_run_id=simulation_run_id,
            source_agent_id=source_uuid,
            target_agent_id=target_uuid,
            action_type=change_type,
            tick_number=tick_number,
            weight=weight,
            context=str(change),
        )
        db.add(edge)
        edges.append(edge)

    # Also extract from direct influence_agent decisions
    for decision in decisions:
        if decision.action == "influence_agent":
            to_id = decision.params.get("target_agent_id", "")
            if not to_id:
                continue
            try:
                source_uuid = UUID(decision.agent_id)
                target_uuid = UUID(to_id)
            except (ValueError, TypeError):
                continue
            edge = InfluenceEdge(
                simulation_run_id=simulation_run_id,
                source_agent_id=source_uuid,
                target_agent_id=target_uuid,
                action_type="influence_agent",
                tick_number=tick_number,
                weight=0.6,
                context=decision.params.get("method", ""),
            )
            db.add(edge)
            edges.append(edge)

    if edges:
        await db.commit()
        logger.debug("Recorded %d influence edges at tick %d", len(edges), tick_number)

    return edges


def _action_type_to_weight(action_type: str) -> float:
    weights = {
        "alliance_formed": 0.9,
        "alliance_broken": -0.5,
        "influence_attempt": 0.6,
        "escalation": -0.7,
        "de_escalation": 0.4,
    }
    return weights.get(action_type, 0.3)
