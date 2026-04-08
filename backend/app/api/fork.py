"""Fork-from-tick endpoint."""

import logging
import random
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.engine.fork_manager import fork_from_tick
from app.models.simulation import SimulationRun, Tick
from app.models.user import User
from app.schemas.simulation import SimulationResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["fork"])


class ForkRequest(BaseModel):
    new_random_seed: int | None = None
    interventions: list[dict] | None = None
    max_additional_ticks: int | None = None


@router.post(
    "/simulations/{sim_id}/fork-from-tick/{tick_id}",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fork_simulation(
    sim_id: uuid.UUID,
    tick_id: uuid.UUID,
    body: ForkRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> SimulationRun:
    # Verify tick belongs to this simulation
    result = await db.execute(
        select(Tick).where(Tick.id == tick_id, Tick.simulation_run_id == sim_id)
    )
    tick = result.scalars().first()
    if not tick:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tick not found in this simulation",
        )

    seed = body.new_random_seed if body.new_random_seed is not None else random.randint(1, 2**31)

    try:
        forked_run = await fork_from_tick(tick=tick, new_random_seed=seed, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Apply optional max_additional_ticks
    if body.max_additional_ticks is not None:
        forked_run.max_ticks = tick.tick_number + body.max_additional_ticks
        await db.commit()
        await db.refresh(forked_run)

    # Create pending interventions for next tick
    if body.interventions:
        from app.models.intervention import Intervention
        for iv in body.interventions:
            intervention = Intervention(
                simulation_run_id=forked_run.id,
                type=iv.get("type", "inject_event"),
                payload=iv.get("payload", {}),
                description=iv.get("description", ""),
                target_tick=tick.tick_number + 1,
                status="pending",
            )
            db.add(intervention)
        await db.commit()

    background_tasks.add_task(_start_forked_simulation, forked_run.id)
    logger.info("Forked simulation %s from tick %s (new run: %s)", sim_id, tick_id, forked_run.id)
    return forked_run


async def _start_forked_simulation(run_id: uuid.UUID) -> None:
    from app.dependencies import get_session_factory
    from app.engine.orchestrator import SimulationOrchestrator

    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(SimulationRun).where(SimulationRun.id == run_id))
        run = result.scalars().first()
        if not run:
            return
        orch = SimulationOrchestrator(db=db)
        await orch.run_simulation(run)
