from fastapi import APIRouter

from app.api import (
    agents,
    auth,
    ensembles,
    fork,
    ingestion,
    interventions,
    reports,
    scenarios,
    simulation,
    surveys,
    world,
    ws,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(scenarios.router)
router.include_router(world.router)
router.include_router(simulation.router)
router.include_router(interventions.router)
router.include_router(agents.router)
router.include_router(reports.router)
router.include_router(ws.router)
router.include_router(surveys.router)
router.include_router(fork.router)
router.include_router(ensembles.router)
router.include_router(ingestion.router)
