"""Tests for deterministic rule engine."""

import random
import uuid
from unittest.mock import MagicMock

import pytest

from app.engine.rule_engine import apply_rules


def make_mock_agent(name="Agent A", faction="Coalition", status="idle"):
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.name = name
    agent.faction = faction
    agent.status = status
    agent.resources = {"influence": 70.0, "capital": 50.0, "information": 40.0}
    agent.semantic_memory = {}
    return agent


def test_rule_engine_returns_outcomes(sample_world_state):
    agents = [make_mock_agent(f"Agent {i}") for i in range(3)]
    rng = random.Random(42)

    outcomes = apply_rules(sample_world_state, agents, tick_number=1, random_gen=rng)
    assert isinstance(outcomes, list)
    # Should have at least resource_decay outcomes
    rule_types = {o.rule_type for o in outcomes}
    assert "resource_decay" in rule_types


def test_determinism_with_same_seed(sample_world_state):
    agents = [make_mock_agent(f"Agent {i}") for i in range(3)]

    outcomes_1 = apply_rules(sample_world_state, agents, tick_number=3, random_gen=random.Random(42))
    outcomes_2 = apply_rules(sample_world_state, agents, tick_number=3, random_gen=random.Random(42))

    assert len(outcomes_1) == len(outcomes_2)


def test_threshold_trigger_on_kpi_breach(sample_world_state):
    # Set KPI to near-critical
    world = dict(sample_world_state)
    world["kpi_values"] = {"political_stability": 2.0}  # Near zero — should trigger alert
    world["kpis"] = [{"name": "political_stability", "target": 80, "initial_value": 60}]

    agents = []
    rng = random.Random(0)
    outcomes = apply_rules(world, agents, tick_number=1, random_gen=rng)

    threshold_outcomes = [o for o in outcomes if o.rule_type == "threshold_triggers"]
    assert len(threshold_outcomes) > 0
