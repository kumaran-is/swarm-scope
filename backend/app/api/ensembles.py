"""Ensemble API endpoints."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.ensemble import EnsembleRun
from app.models.simulation import SimulationRun
from app.models.user import User
from app.schemas.simulation import SimulationResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ensembles", tags=["ensembles"])


class EnsembleCreateRequest(BaseModel):
    scenario_id: uuid.UUID
    ensemble_size: int = 5
    base_config: dict = {}
    base_seed: int = 42


class EnsembleResponse(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    ensemble_size: int
    base_config: dict
    status: str
    statistics: dict | None
    completed_runs: int = 0


@router.post("", response_model=EnsembleResponse, status_code=status.HTTP_201_CREATED)
async def create_ensemble(
    body: EnsembleCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    ensemble = EnsembleRun(
        scenario_id=body.scenario_id,
        user_id=current_user.id,
        ensemble_size=body.ensemble_size,
        base_config=body.base_config,
        status="pending",
    )
    db.add(ensemble)
    await db.commit()
    await db.refresh(ensemble)

    background_tasks.add_task(_run_ensemble_task, ensemble.id, body.base_seed)
    return _to_response(ensemble, completed_runs=0)


@router.get("", response_model=list[EnsembleResponse])
async def list_ensembles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    result = await db.execute(
        select(EnsembleRun).where(EnsembleRun.user_id == current_user.id)
        .order_by(EnsembleRun.created_at.desc())
    )
    ensembles = result.scalars().all()
    return [_to_response(e, 0) for e in ensembles]


@router.get("/{ensemble_id}", response_model=EnsembleResponse)
async def get_ensemble(
    ensemble_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    e = await _get_or_404(ensemble_id, db)
    completed = await _count_completed_runs(ensemble_id, db)
    return _to_response(e, completed)


@router.get("/{ensemble_id}/runs", response_model=list[SimulationResponse])
async def list_ensemble_runs(
    ensemble_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[SimulationRun]:
    result = await db.execute(
        select(SimulationRun).where(SimulationRun.ensemble_run_id == ensemble_id)
        .order_by(SimulationRun.ensemble_seed_index)
    )
    return list(result.scalars().all())


@router.get("/{ensemble_id}/statistics")
async def get_ensemble_statistics(
    ensemble_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    e = await _get_or_404(ensemble_id, db)
    return e.statistics or {}


@router.get("/{ensemble_id}/kpi/{kpi_name}")
async def get_kpi_detail(
    ensemble_id: uuid.UUID,
    kpi_name: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    e = await _get_or_404(ensemble_id, db)
    stats = e.statistics or {}
    kpi_stats = stats.get("kpi_statistics", {}).get(kpi_name)
    if not kpi_stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"KPI '{kpi_name}' not found in statistics")
    return {"kpi_name": kpi_name, **kpi_stats}


@router.delete("/{ensemble_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ensemble(
    ensemble_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    e = await _get_or_404(ensemble_id, db)
    await db.delete(e)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(e: EnsembleRun, completed_runs: int) -> dict:
    return {
        "id": e.id,
        "scenario_id": e.scenario_id,
        "ensemble_size": e.ensemble_size,
        "base_config": e.base_config,
        "status": e.status,
        "statistics": e.statistics,
        "completed_runs": completed_runs,
    }


async def _get_or_404(ensemble_id: uuid.UUID, db: AsyncSession) -> EnsembleRun:
    result = await db.execute(select(EnsembleRun).where(EnsembleRun.id == ensemble_id))
    e = result.scalars().first()
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ensemble not found")
    return e


async def _count_completed_runs(ensemble_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.ensemble_run_id == ensemble_id,
            SimulationRun.status == "completed",
        )
    )
    return len(result.scalars().all())


async def _run_ensemble_task(ensemble_id: uuid.UUID, base_seed: int) -> None:
    from app.dependencies import get_session_factory
    from app.engine.ensemble_aggregator import aggregate_kpi_trajectories
    from app.engine.ensemble_runner import EnsembleRunner
    from app.models.simulation import Tick

    factory = get_session_factory()

    async with factory() as db:
        result = await db.execute(select(EnsembleRun).where(EnsembleRun.id == ensemble_id))
        ensemble = result.scalars().first()
        if not ensemble:
            return

        ensemble.status = "running"
        await db.commit()

    runner = EnsembleRunner(session_factory=factory)
    async with factory() as db:
        result = await db.execute(select(EnsembleRun).where(EnsembleRun.id == ensemble_id))
        ensemble = result.scalars().first()
        if not ensemble:
            return
        try:
            await runner.run_ensemble(ensemble, base_random_seed=base_seed)
        except Exception as exc:
            logger.error("Ensemble run failed for %s: %s", ensemble_id, exc)

    # Aggregate statistics
    async with factory() as db:
        result = await db.execute(select(EnsembleRun).where(EnsembleRun.id == ensemble_id))
        ensemble = result.scalars().first()
        if not ensemble:
            return

        runs_result = await db.execute(
            select(SimulationRun).where(
                SimulationRun.ensemble_run_id == ensemble_id,
                SimulationRun.status == "completed",
            )
        )
        completed_runs = list(runs_result.scalars().all())

        # Collect KPI data per run
        all_runs_kpi_data = []
        for run in completed_runs:
            ticks_result = await db.execute(
                select(Tick).where(Tick.simulation_run_id == run.id).order_by(Tick.tick_number)
            )
            ticks = ticks_result.scalars().all()
            tick_records = [
                {"tick": t.tick_number, **(t.kpi_values or {})} for t in ticks
            ]
            all_runs_kpi_data.append(tick_records)

        kpi_stats = aggregate_kpi_trajectories(all_runs_kpi_data)
        ensemble.statistics = {"kpi_statistics": kpi_stats, "completed_runs": len(completed_runs)}
        ensemble.status = "completed"
        await db.commit()
        logger.info("Ensemble %s aggregation complete (%d runs)", ensemble_id, len(completed_runs))
