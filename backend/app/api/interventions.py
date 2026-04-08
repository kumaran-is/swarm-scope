"""Intervention CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.intervention import Intervention
from app.schemas.intervention import InterventionCreate, InterventionResponse

router = APIRouter(tags=["interventions"])


@router.post("/simulations/{sim_id}/interventions", response_model=InterventionResponse, status_code=status.HTTP_201_CREATED)
async def create_intervention(
    sim_id: uuid.UUID,
    payload: InterventionCreate,
    db: AsyncSession = Depends(get_db),
):
    iv = Intervention(
        simulation_run_id=sim_id,
        type=payload.type,
        payload=payload.payload,
        description=payload.description,
        target_tick=payload.target_tick,
        status="pending",
    )
    db.add(iv)
    await db.commit()
    await db.refresh(iv)
    return iv


@router.get("/simulations/{sim_id}/interventions", response_model=list[InterventionResponse])
async def list_interventions(sim_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Intervention).where(Intervention.simulation_run_id == sim_id)
    )
    return list(result.scalars().all())


@router.delete("/simulations/{sim_id}/interventions/{iv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_intervention(
    sim_id: uuid.UUID, iv_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Intervention).where(
            Intervention.id == iv_id,
            Intervention.simulation_run_id == sim_id,
        )
    )
    iv = result.scalars().first()
    if not iv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found")
    if iv.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel intervention with status '{iv.status}'",
        )
    iv.status = "cancelled"
    await db.commit()
