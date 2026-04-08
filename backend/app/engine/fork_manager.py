"""
Fork manager: create a new simulation run starting from a tick snapshot.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.state_manager import restore_from_snapshot
from app.models.simulation import SimulationRun, Tick

logger = logging.getLogger(__name__)


async def fork_from_tick(
    tick: Tick,
    new_random_seed: int,
    db: AsyncSession,
) -> SimulationRun:
    """
    Create a new SimulationRun forked from an existing tick's snapshot.
    The new run starts at tick_number+1 with the snapshot as initial state.
    """
    if not tick.snapshot:
        raise ValueError(f"Tick {tick.id} has no snapshot — cannot fork")

    # Restore state from snapshot
    world_state, agent_states = restore_from_snapshot(tick.snapshot)

    # Get the original run to copy config
    original_result = await db.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(SimulationRun).where(
            SimulationRun.id == tick.simulation_run_id
        )
    )
    original_run = original_result.scalars().first()
    if not original_run:
        raise ValueError(f"Original simulation run not found for tick {tick.id}")

    # Create new forked run
    forked_run = SimulationRun(
        scenario_id=original_run.scenario_id,
        random_seed=new_random_seed,
        status="pending",
        current_tick=tick.tick_number,
        max_ticks=original_run.max_ticks,
        config={**original_run.config, "forked_from_tick": tick.tick_number},
        forked_from_tick_id=tick.id,
    )
    db.add(forked_run)
    await db.commit()
    await db.refresh(forked_run)

    logger.info(
        "Forked simulation %s from tick %d (original: %s, new seed: %d)",
        forked_run.id,
        tick.tick_number,
        original_run.id,
        new_random_seed,
    )
    return forked_run
