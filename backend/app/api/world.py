"""World model endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.world import WorldModel
from app.schemas.world import WorldModelResponse, WorldModelUpdate

router = APIRouter(tags=["world"])


@router.get("/scenarios/{scenario_id}/world", response_model=WorldModelResponse)
async def get_world_model(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    world = await _get_or_404(scenario_id, db)
    return world


@router.put("/scenarios/{scenario_id}/world", response_model=WorldModelResponse)
async def update_world_model(
    scenario_id: uuid.UUID,
    update: WorldModelUpdate,
    db: AsyncSession = Depends(get_db),
):
    world = await _get_or_404(scenario_id, db)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(world, field, value)
    await db.commit()
    await db.refresh(world)
    return world


@router.get("/scenarios/{scenario_id}/knowledge-graph")
async def get_knowledge_graph(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return D3-compatible nodes/edges for the knowledge graph viewer."""
    world = await _get_or_404(scenario_id, db)

    nodes = []
    edges = []

    # Entity nodes
    for entity in (world.entities or []):
        if isinstance(entity, dict):
            nodes.append({
                "id": entity.get("name", ""),
                "label": entity.get("name", ""),
                "group": "entity",
                "type": entity.get("type", ""),
            })

    # Faction nodes
    for faction in (world.factions or []):
        if isinstance(faction, dict):
            nodes.append({
                "id": faction.get("name", ""),
                "label": faction.get("name", ""),
                "group": "faction",
            })

    # Tension edges
    for tension in (world.tensions or []):
        if isinstance(tension, dict):
            between = tension.get("between", [])
            if len(between) >= 2:
                edges.append({
                    "source": between[0],
                    "target": between[1],
                    "type": "tension",
                    "intensity": tension.get("intensity", 5),
                    "description": tension.get("description", ""),
                })

    return {"nodes": nodes, "edges": edges}


async def _get_or_404(scenario_id: uuid.UUID, db: AsyncSession) -> WorldModel:
    result = await db.execute(select(WorldModel).where(WorldModel.scenario_id == scenario_id))
    world = result.scalars().first()
    if not world:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World model not found")
    return world
