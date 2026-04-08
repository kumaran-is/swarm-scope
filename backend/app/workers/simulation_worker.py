"""
Simulation worker: runs the tick loop in the background via FastAPI BackgroundTasks.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.orchestrator import SimulationOrchestrator
from app.gemini.client import GeminiClient
from app.models.simulation import SimulationRun

logger = logging.getLogger(__name__)


async def run_simulation_background(
    simulation_run: SimulationRun,
    db: AsyncSession,
    client: GeminiClient | None = None,
    broadcast_fn=None,
) -> None:
    """
    Entry point for background simulation execution.
    Called from the API layer via BackgroundTasks.
    """
    orchestrator = SimulationOrchestrator(
        db=db,
        client=client,
        broadcast_fn=broadcast_fn,
    )
    try:
        await orchestrator.run_simulation(simulation_run)
    except Exception as exc:
        logger.error("Background simulation %s failed: %s", simulation_run.id, exc)
        simulation_run.status = "failed"
        await db.commit()
