"""Tests for selective activation scoring."""

import random
import uuid
from unittest.mock import MagicMock

import pytest

from app.engine.activation import compute_activation_scores


def make_mock_agent(name="Agent A", faction="Coalition", status="idle"):
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.name = name
    agent.faction = faction
    agent.status = status
    agent.goals = [{"description": "Pass the bill", "priority": 1}]
    agent.resources = {"influence": 70, "capital": 50}
    return agent


def test_activation_scores_sorted_descending(sample_world_state):
    agents = [make_mock_agent(f"Agent {i}") for i in range(5)]
    last_activated = {}
    rng = random.Random(42)

    scored = compute_activation_scores(agents, sample_world_state, current_tick=1, last_activated=last_activated, random_gen=rng)

    assert len(scored) == 5
    scores = [s for _, s in scored]
    assert scores == sorted(scores, reverse=True), "Scores should be sorted descending"


def test_eliminated_agent_gets_zero_score(sample_world_state):
    agent = make_mock_agent(status="eliminated")
    last_activated = {}
    rng = random.Random(42)

    scored = compute_activation_scores([agent], sample_world_state, current_tick=1, last_activated=last_activated, random_gen=rng)
    assert scored[0][1] == 0.0


def test_same_seed_same_scores(sample_world_state):
    agents = [make_mock_agent(f"Agent {i}") for i in range(3)]
    last_activated = {}

    scored_1 = compute_activation_scores(agents, sample_world_state, current_tick=5, last_activated=last_activated, random_gen=random.Random(99))
    scored_2 = compute_activation_scores(agents, sample_world_state, current_tick=5, last_activated=last_activated, random_gen=random.Random(99))

    for (a1, s1), (a2, s2) in zip(scored_1, scored_2):
        assert s1 == s2, "Same seed must produce same scores"
