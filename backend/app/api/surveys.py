"""Survey endpoints."""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.ingestion import Survey
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["surveys"])


class SurveyCreate(BaseModel):
    question: str
    target_agent_ids: list[str]
    response_format: str = "free_text"


class SurveyResponse(BaseModel):
    id: uuid.UUID
    simulation_run_id: uuid.UUID
    question: str
    target_agent_ids: list
    response_format: str | None
    responses: dict | None
    aggregate_analysis: dict | None


@router.post("/simulations/{sim_id}/survey", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(
    sim_id: uuid.UUID,
    body: SurveyCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Survey:
    survey = Survey(
        simulation_run_id=sim_id,
        question=body.question,
        target_agent_ids=body.target_agent_ids,
        response_format=body.response_format,
    )
    db.add(survey)
    await db.commit()
    await db.refresh(survey)
    background_tasks.add_task(_run_survey_task, survey.id, sim_id)
    return survey


@router.get("/simulations/{sim_id}/surveys", response_model=list[SurveyResponse])
async def list_surveys(
    sim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[Survey]:
    result = await db.execute(
        select(Survey).where(Survey.simulation_run_id == sim_id).order_by(Survey.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/simulations/{sim_id}/surveys/{survey_id}", response_model=SurveyResponse)
async def get_survey(
    sim_id: uuid.UUID,
    survey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Survey:
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.simulation_run_id == sim_id)
    )
    survey = result.scalars().first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    return survey


async def _run_survey_task(survey_id: uuid.UUID, sim_id: uuid.UUID) -> None:
    from app.dependencies import get_session_factory
    from app.engine.survey_executor import execute_survey
    from app.models.agent import Agent

    factory = get_session_factory()
    async with factory() as db:
        survey_result = await db.execute(select(Survey).where(Survey.id == survey_id))
        survey = survey_result.scalars().first()
        if not survey:
            return

        from app.models.simulation import SimulationRun, Tick

        run_result = await db.execute(select(SimulationRun).where(SimulationRun.id == sim_id))
        run = run_result.scalars().first()
        scenario_id = run.scenario_id if run else None

        agents_result = await db.execute(
            select(Agent).where(Agent.scenario_id == scenario_id) if scenario_id
            else select(Agent).where(Agent.id == None)  # noqa: E711
        )
        agents = list(agents_result.scalars().all())

        last_tick_result = await db.execute(
            select(Tick).where(Tick.simulation_run_id == sim_id)
            .order_by(Tick.tick_number.desc()).limit(1)
        )
        last_tick = last_tick_result.scalars().first()
        current_tick = last_tick.tick_number if last_tick else 0

        try:
            await execute_survey(
                survey=survey,
                agents=agents,
                world_state={},
                scenario_name="simulation",
                current_tick=current_tick,
                db=db,
            )
        except Exception as exc:
            logger.error("Survey task failed for %s: %s", survey_id, exc)
