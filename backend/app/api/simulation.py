"""Simulation run endpoints."""

import logging
import random
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.report import InfluenceEdge
from app.models.simulation import SimulationRun, Tick
from app.models.user import User
from app.schemas.simulation import SimulationCreate, SimulationResponse, TickResponse
from app.utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)
router = APIRouter(tags=["simulation"])


@router.post("/simulations", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    payload: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    seed = payload.random_seed if payload.random_seed is not None else random.randint(1, 2**31)
    run = SimulationRun(
        scenario_id=payload.scenario_id,
        random_seed=seed,
        status="pending",
        current_tick=0,
        max_ticks=payload.max_ticks,
        config=payload.config,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    background_tasks.add_task(_run_simulation_task, run.id)
    return run


@router.get("/simulations/{sim_id}", response_model=SimulationResponse)
async def get_simulation(
    sim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    return await _get_or_404(sim_id, db)


@router.post("/simulations/{sim_id}/pause", response_model=dict)
async def pause_simulation(sim_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await _get_or_404(sim_id, db)
    run.status = "paused"
    await db.commit()
    # Orchestrator checks this via Redis or in-memory flag
    return {"status": "pausing", "simulation_id": str(sim_id)}


@router.post("/simulations/{sim_id}/resume", response_model=dict)
async def resume_simulation(sim_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await _get_or_404(sim_id, db)
    run.status = "running"
    await db.commit()
    return {"status": "resuming", "simulation_id": str(sim_id)}


@router.post("/simulations/{sim_id}/stop", response_model=dict)
async def stop_simulation(sim_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await _get_or_404(sim_id, db)
    run.status = "failed"  # "stopped" not in enum — use failed to halt
    await db.commit()
    return {"status": "stopping", "simulation_id": str(sim_id)}


@router.get("/simulations/{sim_id}/ticks", response_model=list[TickResponse])
async def list_ticks(
    sim_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tick)
        .where(Tick.simulation_run_id == sim_id)
        .order_by(Tick.tick_number)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/simulations/{sim_id}/ticks/{tick_num}", response_model=TickResponse)
async def get_tick(sim_id: uuid.UUID, tick_num: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tick).where(
            Tick.simulation_run_id == sim_id, Tick.tick_number == tick_num
        )
    )
    tick = result.scalars().first()
    if not tick:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tick {tick_num} not found")
    return tick


@router.get("/simulations/{sim_id}/cost")
async def get_simulation_cost(
    sim_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Return Gemini cost breakdown for a simulation run."""

    from app.dependencies import get_redis as _get_redis
    redis = await _get_redis()
    tracker = CostTracker(redis=redis)
    cost = await tracker.get_run_cost(sim_id)
    cost["simulation_run_id"] = str(sim_id)
    return cost


@router.get("/simulations/{sim_id}/influence-graph")
async def get_influence_graph(
    sim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Return accumulated influence graph for the simulation."""
    result = await db.execute(
        select(InfluenceEdge).where(InfluenceEdge.simulation_run_id == sim_id)
    )
    edges = list(result.scalars().all())

    # Collect unique agent IDs
    agent_ids: set[str] = set()
    for edge in edges:
        agent_ids.add(str(edge.source_agent_id))
        agent_ids.add(str(edge.target_agent_id))

    # Aggregate edges
    edge_map: dict[tuple[str, str], dict] = {}
    for edge in edges:
        key = (str(edge.source_agent_id), str(edge.target_agent_id))
        if key not in edge_map:
            edge_map[key] = {"source": key[0], "target": key[1], "weight": 0.0, "actions": []}
        edge_map[key]["weight"] += edge.weight or 0.0
        edge_map[key]["actions"].append(edge.action_type)

    return {
        "nodes": [{"id": aid, "label": aid[:8], "total_influence": 0.0} for aid in agent_ids],
        "edges": list(edge_map.values()),
    }


@router.get("/simulations/{sim_id}/influence-graph/agent/{agent_id}")
async def get_agent_ego_network(
    sim_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Return ego network for a single agent."""
    from sqlalchemy import or_
    result = await db.execute(
        select(InfluenceEdge).where(
            InfluenceEdge.simulation_run_id == sim_id,
            or_(
                InfluenceEdge.source_agent_id == agent_id,
                InfluenceEdge.target_agent_id == agent_id,
            ),
        )
    )
    edges = list(result.scalars().all())

    agent_ids: set[str] = set()
    for edge in edges:
        agent_ids.add(str(edge.source_agent_id))
        agent_ids.add(str(edge.target_agent_id))

    return {
        "nodes": [{"id": aid, "label": aid[:8], "is_ego": aid == str(agent_id)} for aid in agent_ids],
        "edges": [
            {
                "source": str(e.source_agent_id),
                "target": str(e.target_agent_id),
                "weight": e.weight,
                "action_type": e.action_type,
            }
            for e in edges
        ],
    }


async def _run_simulation_task(sim_id: uuid.UUID) -> None:
    from app.dependencies import get_session_factory
    from app.engine.orchestrator import SimulationOrchestrator

    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(SimulationRun).where(SimulationRun.id == sim_id))
        run = result.scalars().first()
        if not run:
            logger.error("Simulation run %s not found in background task", sim_id)
            return
        orch = SimulationOrchestrator(db=db)
        await orch.run_simulation(run)


async def _get_or_404(sim_id: uuid.UUID, db: AsyncSession) -> SimulationRun:
    result = await db.execute(select(SimulationRun).where(SimulationRun.id == sim_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return run
