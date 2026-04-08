"""
Determinism auditor: track where stochasticity entered the simulation.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StochasticEntry:
    tick: int
    source: str  # "gemini", "random_jitter", "activation_score", etc.
    description: str
    seed_value: float | None = None


class DeterminismAuditor:
    """Tracks all non-deterministic events in a simulation run."""

    def __init__(self) -> None:
        self._entries: list[StochasticEntry] = []

    def record(
        self,
        tick: int,
        source: str,
        description: str,
        seed_value: float | None = None,
    ) -> None:
        entry = StochasticEntry(tick=tick, source=source, description=description, seed_value=seed_value)
        self._entries.append(entry)
        logger.debug("Stochastic event: tick=%d source=%s desc=%s", tick, source, description)

    def get_report(self) -> dict[str, Any]:
        sources: dict[str, int] = {}
        for entry in self._entries:
            sources[entry.source] = sources.get(entry.source, 0) + 1
        return {
            "total_stochastic_events": len(self._entries),
            "by_source": sources,
            "entries": [e.__dict__ for e in self._entries],
        }
