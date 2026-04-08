"""
Intervention handler: apply God's-eye interventions to the simulation mid-tick.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.intervention import Intervention

logger = logging.getLogger(__name__)


@dataclass
class InterventionResult:
    intervention_id: str
    success: bool
    description: str
    effects: dict[str, Any]


async def get_pending_interventions(
    simulation_run_id: UUID,
    tick_number: int,
    db: AsyncSession,
) -> list[Intervention]:
    """Return pending interventions for this tick (target_tick is None or <= tick_number)."""
    result = await db.execute(
        select(Intervention).where(
            Intervention.simulation_run_id == simulation_run_id,
            Intervention.status == "pending",
            (Intervention.target_tick.is_(None)) | (Intervention.target_tick <= tick_number),
        )
    )
    return list(result.scalars().all())


async def apply_intervention(
    intervention: Intervention,
    world_state: dict[str, Any],
    agents: list[Agent],
    db: AsyncSession,
    tick_number: int,
) -> InterventionResult:
    """
    Apply a single intervention to the current world state.
    Marks the intervention as applied.
    """
    payload = intervention.payload or {}
    effects: dict[str, Any] = {}
    success = True
    description = intervention.description or f"Intervention {intervention.type}"

    try:
        if intervention.type == "inject_event":
            event_description = payload.get("description", "External event")
            affected_entities = payload.get("affected_entities", [])
            severity = payload.get("severity", "medium")

            world_state.setdefault("recent_events", []).append(
                {
                    "type": "injected_event",
                    "description": event_description,
                    "affected_entities": affected_entities,
                    "severity": severity,
                    "tick": tick_number,
                }
            )
            effects = {"event_injected": event_description, "severity": severity}

        elif intervention.type == "modify_agent":
            target_agent_id = payload.get("agent_id", "")
            target_agent = next(
                (a for a in agents if str(a.id) == target_agent_id), None
            )
            if target_agent is None:
                raise ValueError(f"Agent {target_agent_id} not found")

            if "goals" in payload:
                target_agent.goals = payload["goals"]
            if "resources" in payload:
                resources = dict(target_agent.resources or {})
                resources.update(payload["resources"])
                target_agent.resources = resources
            if "status" in payload:
                target_agent.status = payload["status"]

            effects = {"agent_modified": target_agent_id, "changes": payload}

        elif intervention.type == "modify_world":
            resource_changes = payload.get("resource_changes", {})
            kpi_changes = payload.get("kpi_changes", {})
            constraint_changes = payload.get("constraint_changes", {})

            kpi_values = dict(world_state.get("kpi_values", {}))
            kpi_values.update(kpi_changes)
            world_state["kpi_values"] = kpi_values
            effects = {
                "resource_changes": resource_changes,
                "kpi_changes": kpi_changes,
                "constraint_changes": constraint_changes,
            }
        else:
            logger.warning("Unknown intervention type: %s", intervention.type)
            success = False
            description = f"Unknown intervention type: {intervention.type}"

    except Exception as exc:
        logger.error("Intervention %s failed: %s", intervention.id, exc)
        success = False
        description = f"Intervention failed: {exc}"

    # Mark as applied
    intervention.status = "applied"
    intervention.applied_at_tick = tick_number
    await db.commit()

    return InterventionResult(
        intervention_id=str(intervention.id),
        success=success,
        description=description,
        effects=effects,
    )
