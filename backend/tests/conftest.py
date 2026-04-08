"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def sample_world_state():
    return {
        "summary": "A policy negotiation scenario",
        "entities": [{"name": "Minister A", "type": "person", "description": "Lead negotiator"}],
        "factions": [{"name": "Coalition", "goals": ["Pass bill"], "resources": ["votes"], "relationships": {}}],
        "tensions": [{"between": ["Coalition", "Opposition"], "description": "Budget disagreement", "intensity": 7}],
        "kpis": [{"name": "political_stability", "description": "Overall stability", "unit": "index", "initial_value": 60, "target": 80}],
        "kpi_values": {"political_stability": 60.0},
        "recent_events": [],
        "conflicts": {},
        "alerts": [],
    }
