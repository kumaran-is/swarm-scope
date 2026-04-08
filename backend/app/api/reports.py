"""Report generation and retrieval endpoints."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.report import Report
from app.models.simulation import SimulationRun
from app.schemas.report import ReportGenerateRequest, ReportResponse

router = APIRouter(tags=["reports"])


@router.post("/simulations/{sim_id}/report", response_model=dict)
async def generate_report(
    sim_id: uuid.UUID,
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    run = await _get_run_or_404(sim_id, db)
    if run.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Simulation must be complete before generating a report",
        )

    background_tasks.add_task(_generate_report_task, sim_id)
    return {"status": "generating", "simulation_id": str(sim_id)}


@router.get("/simulations/{sim_id}/report", response_model=ReportResponse)
async def get_report(sim_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Report).where(Report.simulation_run_id == sim_id)
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


async def _generate_report_task(sim_id: uuid.UUID) -> None:
    from app.dependencies import get_session_factory
    from app.models.scenario import Scenario
    from app.workers.report_worker import generate_report_background

    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(SimulationRun).where(SimulationRun.id == sim_id))
        run = result.scalars().first()
        if not run:
            return
        scenario_result = await db.execute(
            select(Scenario).where(Scenario.id == run.scenario_id)
        )
        scenario = scenario_result.scalars().first()
        scenario_name = scenario.name if scenario else "Unknown"
        domain = scenario.domain if scenario else "general"
        await generate_report_background(run, scenario_name, domain, db)


async def _get_run_or_404(sim_id: uuid.UUID, db: AsyncSession) -> SimulationRun:
    result = await db.execute(select(SimulationRun).where(SimulationRun.id == sim_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return run
