"""
State manager: apply agent decisions and rule outcomes atomically to world state.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.engine.decision_engine import AgentDecision
from app.engine.rule_engine import RuleOutcome
from app.models.agent import Agent

logger = logging.getLogger(__name__)


@dataclass
class WorldStateDelta:
    tick_number: int
    resource_changes: dict[str, dict[str, float]] = field(default_factory=dict)
    relationship_changes: list[dict[str, Any]] = field(default_factory=list)
    new_events: list[str] = field(default_factory=list)
    kpi_changes: dict[str, float] = field(default_factory=dict)
    applied_actions: list[str] = field(default_factory=list)


def apply_actions(
    world_state: dict[str, Any],
    agents: list[Agent],
    decisions: list[AgentDecision],
    rule_outcomes: list[RuleOutcome],
    tick_number: int,
) -> WorldStateDelta:
    """
    Apply all agent decisions and rule outcomes atomically to world state.
    Validates preconditions before applying effects.
    Returns a WorldStateDelta describing what changed this tick.
    """
    delta = WorldStateDelta(tick_number=tick_number)
    agent_map = {str(a.id): a for a in agents}

    # Apply rule outcomes first (deterministic)
    for outcome in rule_outcomes:
        _apply_rule_outcome(outcome, world_state, agents, delta)

    # Apply agent decisions
    for decision in decisions:
        agent = agent_map.get(decision.agent_id)
        if agent is None:
            logger.warning("Agent %s not found in state — skipping", decision.agent_id)
            continue
        _apply_decision(decision, agent, agents, world_state, delta)

    # Recompute KPI values
    _update_kpis(world_state, agents, delta)

    return delta


def _apply_rule_outcome(
    outcome: RuleOutcome,
    world_state: dict[str, Any],
    agents: list[Agent],
    delta: WorldStateDelta,
) -> None:
    delta.new_events.append(f"[rule:{outcome.rule_type}] {outcome.description}")
    effects = outcome.effects or {}

    if outcome.rule_type == "resource_decay" and outcome.agent_id:
        agent = next((a for a in agents if str(a.id) == outcome.agent_id), None)
        if agent and "resources" in effects:
            delta.resource_changes[outcome.agent_id] = effects["resources"]

    elif outcome.rule_type == "threshold_triggers":
        world_state.setdefault("alerts", []).append(outcome.description)


def _apply_decision(
    decision: AgentDecision,
    agent: Agent,
    all_agents: list[Agent],
    world_state: dict[str, Any],
    delta: WorldStateDelta,
) -> None:
    action = decision.action
    params = decision.params or {}
    delta.applied_actions.append(f"{agent.name}:{action}")

    if action == "form_alliance":
        target_id = params.get("target_agent_id", "")
        terms = params.get("terms", "")
        # Update semantic memory to record alliance
        semantic = dict(agent.semantic_memory or {})
        alliances = dict(semantic.get("alliances", {}))
        alliances[target_id] = 1.0
        semantic["alliances"] = alliances
        agent.semantic_memory = semantic
        delta.relationship_changes.append(
            {"type": "alliance_formed", "from": str(agent.id), "to": target_id, "terms": terms}
        )

    elif action == "break_alliance":
        target_id = params.get("target_agent_id", "")
        semantic = dict(agent.semantic_memory or {})
        alliances = dict(semantic.get("alliances", {}))
        alliances.pop(target_id, None)
        semantic["alliances"] = alliances
        agent.semantic_memory = semantic
        delta.relationship_changes.append(
            {"type": "alliance_broken", "from": str(agent.id), "to": target_id}
        )

    elif action == "publish_statement":
        content = params.get("content", "")
        audience = params.get("audience", "public")
        tone = params.get("tone", "neutral")
        world_state.setdefault("recent_events", []).append(
            {
                "type": "statement",
                "agent": agent.name,
                "faction": agent.faction,
                "content": content,
                "audience": audience,
                "tone": tone,
                "description": f"{agent.name} published a {tone} statement to {audience}",
            }
        )

    elif action == "reallocate_resource":
        resource_type = params.get("resource_type", "influence")
        amount = float(params.get("amount", 0))
        # Validate: agent must have sufficient resources
        resources = dict(agent.resources or {})
        current = float(resources.get(resource_type, 0))
        if amount > current:
            logger.warning(
                "Agent %s cannot reallocate %s=%s (only has %s)",
                agent.name, resource_type, amount, current
            )
            return
        resources[resource_type] = max(0, current - amount)
        agent.resources = resources
        delta.resource_changes[str(agent.id)] = {resource_type: -amount}

    elif action == "escalate_conflict":
        target = params.get("target", "")
        method = params.get("method", "")
        intensity = float(params.get("intensity", 5))
        world_state.setdefault("conflicts", {}).setdefault(target, []).append(
            {"initiator": str(agent.id), "method": method, "intensity": intensity}
        )

    elif action == "de_escalate_conflict":
        target = params.get("target", "")
        concession = params.get("concession", "")
        world_state.setdefault("recent_events", []).append(
            {
                "type": "de_escalation",
                "agent": agent.name,
                "target": target,
                "concession": concession,
                "description": f"{agent.name} offered de-escalation to {target}",
            }
        )

    elif action == "gather_information":
        # Boost information resource
        resources = dict(agent.resources or {})
        resources["information"] = min(100, float(resources.get("information", 50)) + 2.0)
        agent.resources = resources

    elif action == "influence_agent":
        target_id = params.get("target_agent_id", "")
        method = params.get("method", "")
        goal = params.get("goal", "")
        delta.relationship_changes.append(
            {"type": "influence_attempt", "from": str(agent.id), "to": target_id, "method": method, "goal": goal}
        )

    elif action == "change_strategy":
        new_strategy = params.get("new_strategy", "")
        semantic = dict(agent.semantic_memory or {})
        semantic["current_strategy"] = new_strategy
        agent.semantic_memory = semantic

    elif action == "do_nothing":
        pass  # explicit no-op


def _update_kpis(
    world_state: dict[str, Any],
    agents: list[Agent],
    delta: WorldStateDelta,
) -> None:
    """Recompute KPI values from current world state."""
    kpi_defs = world_state.get("kpis", [])
    kpi_values = dict(world_state.get("kpi_values", {}))

    for kpi in kpi_defs:
        if not isinstance(kpi, dict):
            continue
        name = kpi.get("name", "")
        if not name:
            continue
        # Simple heuristic: average agent resource as proxy for unnamed KPIs
        old_val = float(kpi_values.get(name) or kpi.get("initial_value") or 50)
        # Drift KPI based on conflicts/events
        conflicts = len(world_state.get("conflicts", {}))
        recent = len(world_state.get("recent_events", []))
        drift = -0.5 * conflicts + 0.1 * recent
        new_val = max(0.0, min(100.0, old_val + drift))
        kpi_values[name] = round(new_val, 2)
        if abs(new_val - old_val) > 0.1:
            delta.kpi_changes[name] = new_val - old_val

    world_state["kpi_values"] = kpi_values


def take_snapshot(world_state: dict[str, Any], agents: list[Agent]) -> dict[str, Any]:
    """Serialize the full world state + agent states for replay/forking."""

    agent_snapshots = []
    for a in agents:
        agent_snapshots.append(
            {
                "id": str(a.id),
                "name": a.name,
                "role": a.role,
                "faction": a.faction,
                "status": a.status,
                "personality": a.personality,
                "goals": a.goals,
                "resources": a.resources,
                "activation_score": a.activation_score,
                "working_memory": a.working_memory,
                "episodic_memory": a.episodic_memory,
                "semantic_memory": a.semantic_memory,
            }
        )
    return {
        "world_state": world_state,
        "agents": agent_snapshots,
    }


def restore_from_snapshot(
    snapshot: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Restore world state and agent state dicts from a snapshot (for forking)."""
    return snapshot.get("world_state", {}), snapshot.get("agents", [])
