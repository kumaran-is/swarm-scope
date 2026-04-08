"""
Rule engine: deterministic rules that run BEFORE Gemini calls each tick.

Rules are deterministic — same input + same seed = same output.
Never use random.random() — always use the seeded random.Random instance.
"""

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from app.models.agent import Agent

logger = logging.getLogger(__name__)


@dataclass
class RuleOutcome:
    rule_type: str
    agent_id: str | None
    description: str
    effects: dict[str, Any] = field(default_factory=dict)


RULE_TYPES = [
    "resource_decay",
    "alliance_maintenance",
    "threshold_triggers",
    "proximity_effects",
    "scheduled_events",
]


def apply_rules(
    world_state: dict[str, Any],
    agents: list[Agent],
    tick_number: int,
    random_gen: random.Random,
    resource_decay_rate: float = 0.02,
    alliance_decay_rate: float = 0.05,
) -> list[RuleOutcome]:
    """
    Apply all deterministic rules for this tick.
    Returns a list of RuleOutcome records describing what changed.
    """
    outcomes: list[RuleOutcome] = []

    outcomes.extend(_resource_decay(agents, random_gen, decay_rate=resource_decay_rate))
    outcomes.extend(_alliance_maintenance(agents, random_gen, decay_rate=alliance_decay_rate))
    outcomes.extend(_threshold_triggers(world_state, agents, tick_number))
    outcomes.extend(_proximity_effects(agents, world_state, random_gen))
    outcomes.extend(_scheduled_events(world_state, tick_number))

    logger.debug("Rule engine applied %d outcomes at tick %d", len(outcomes), tick_number)
    return outcomes


def _resource_decay(
    agents: list[Agent],
    random_gen: random.Random,
    decay_rate: float,
) -> list[RuleOutcome]:
    """Resources deplete slightly each tick (drift + variance)."""
    outcomes = []
    for agent in agents:
        if agent.status in ("eliminated",):
            continue
        resources = dict(agent.resources) if isinstance(agent.resources, dict) else {}
        changed = False
        for resource_key in ("influence", "capital", "information"):
            current = resources.get(resource_key, 50)
            # Small random decay with seeded RNG
            decay = decay_rate * (1 + random_gen.uniform(-0.3, 0.3))
            new_value = max(0.0, current - decay * current)
            if abs(new_value - current) > 0.01:
                resources[resource_key] = round(new_value, 2)
                changed = True
        if changed:
            agent.resources = resources
            outcomes.append(
                RuleOutcome(
                    rule_type="resource_decay",
                    agent_id=str(agent.id),
                    description=f"Resources decayed for {agent.name}",
                    effects={"resources": resources},
                )
            )
    return outcomes


def _alliance_maintenance(
    agents: list[Agent],
    random_gen: random.Random,
    decay_rate: float,
) -> list[RuleOutcome]:
    """Alliance strength weakens without recent interaction."""
    outcomes = []
    for agent in agents:
        semantic = dict(agent.semantic_memory) if isinstance(agent.semantic_memory, dict) else {}
        alliances = semantic.get("alliances", {})
        if not isinstance(alliances, dict):
            continue
        changed = False
        for ally_id, strength in list(alliances.items()):
            new_strength = max(0.0, float(strength) - decay_rate)
            if new_strength < 0.1:
                del alliances[ally_id]
                outcomes.append(
                    RuleOutcome(
                        rule_type="alliance_maintenance",
                        agent_id=str(agent.id),
                        description=f"Alliance dissolved for {agent.name} with {ally_id}",
                        effects={"dissolved_alliance": ally_id},
                    )
                )
            else:
                alliances[ally_id] = round(new_strength, 3)
            changed = True
        if changed:
            semantic["alliances"] = alliances
            agent.semantic_memory = semantic
    return outcomes


def _threshold_triggers(
    world_state: dict[str, Any],
    agents: list[Agent],
    tick_number: int,
) -> list[RuleOutcome]:
    """If a KPI crosses its threshold, generate a world event."""
    outcomes = []
    kpi_values = world_state.get("kpi_values", {})
    kpi_definitions = world_state.get("kpis", [])

    for kpi_def in kpi_definitions:
        if not isinstance(kpi_def, dict):
            continue
        name = kpi_def.get("name", "")
        target = float(kpi_def.get("target", 50))
        current = float(kpi_values.get(name, kpi_def.get("initial_value", 50)))

        # Alert if within 10% of threshold breach
        if current < target * 0.1 or current > target * 1.9:
            outcomes.append(
                RuleOutcome(
                    rule_type="threshold_triggers",
                    agent_id=None,
                    description=f"KPI threshold alert: {name}={current:.1f} (target={target})",
                    effects={"kpi_name": name, "current": current, "target": target},
                )
            )
    return outcomes


def _proximity_effects(
    agents: list[Agent],
    world_state: dict[str, Any],
    random_gen: random.Random,
) -> list[RuleOutcome]:
    """Agents in the same faction influence each other's resources."""
    outcomes: list[RuleOutcome] = []
    faction_groups: dict[str, list[Agent]] = {}
    for agent in agents:
        if agent.faction:
            faction_groups.setdefault(agent.faction, []).append(agent)

    for faction, members in faction_groups.items():
        if len(members) < 2:
            continue
        # Compute faction average influence
        avg_influence = sum(
            (a.resources.get("influence", 50) if isinstance(a.resources, dict) else 50)
            for a in members
        ) / len(members)

        for agent in members:
            resources = dict(agent.resources) if isinstance(agent.resources, dict) else {}
            current = float(resources.get("influence", 50))
            # Pull toward faction average with small random variance
            pull = 0.05 * (avg_influence - current) + random_gen.uniform(-0.5, 0.5)
            new_influence = max(0.0, min(100.0, current + pull))
            if abs(new_influence - current) > 0.1:
                resources["influence"] = round(new_influence, 2)
                agent.resources = resources

    return outcomes


def _scheduled_events(
    world_state: dict[str, Any],
    tick_number: int,
) -> list[RuleOutcome]:
    """Pre-programmed world events that trigger at specific ticks."""
    outcomes = []
    scheduled = world_state.get("scheduled_events", [])
    for event in scheduled:
        if not isinstance(event, dict):
            continue
        if event.get("tick") == tick_number:
            outcomes.append(
                RuleOutcome(
                    rule_type="scheduled_events",
                    agent_id=None,
                    description=event.get("description", f"Scheduled event at tick {tick_number}"),
                    effects=event.get("effects", {}),
                )
            )
    return outcomes
