"""Scenario CRUD + file upload endpoints."""

import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.engine.agent_generator import generate_agents
from app.engine.world_compiler import compile_world
from app.gemini.client import GeminiClient
from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.scenario import ScenarioResponse, ScenarioUpdate
from app.utils.file_parser import parse_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    name: str = Form(...),
    description: str | None = Form(None),
    domain: str = Form("general"),
    config: str = Form("{}"),
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a scenario, optionally uploading a source document."""
    import json

    settings = get_settings()
    source_text: str | None = None
    source_file_path: str | None = None

    if file:
        # Validate file size
        contents = await file.read()
        if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
            )

        # Save file
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename or "").suffix.lower() if file.filename else ".txt"
        file_path = upload_dir / f"{file_id}{file_ext}"
        with open(file_path, "wb") as f:
            f.write(contents)

        source_file_path = str(file_path)
        try:
            source_text = parse_file(str(file_path))
        except Exception as exc:
            logger.error("File parse error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not parse file: {exc}",
            ) from exc

    try:
        config_dict = json.loads(config)
    except json.JSONDecodeError:
        config_dict = {}

    scenario = Scenario(
        name=name,
        description=description,
        domain=domain,
        config=config_dict,
        source_file_path=source_file_path,
        source_text=source_text,
        status="draft",
        user_id=current_user.id,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Scenario).where(Scenario.user_id == current_user.id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = await _get_or_404(scenario_id, db, current_user.id)
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: uuid.UUID,
    update: ScenarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = await _get_or_404(scenario_id, db, current_user.id)
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(scenario, field, value)
    await db.commit()
    await db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = await _get_or_404(scenario_id, db, current_user.id)
    await db.delete(scenario)
    await db.commit()


@router.post("/{scenario_id}/compile", response_model=dict)
async def compile_scenario_world(
    scenario_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger world model compilation from source text (background task)."""
    scenario = await _get_or_404(scenario_id, db, current_user.id)
    if not scenario.source_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scenario has no source text — upload a file first",
        )

    scenario.status = "compiling"
    await db.commit()

    background_tasks.add_task(_compile_world_task, scenario_id, scenario.source_text)
    return {"status": "compiling", "scenario_id": str(scenario_id)}


@router.post("/{scenario_id}/generate-agents", response_model=dict)
async def generate_agents_endpoint(
    scenario_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    count: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate agent population from compiled world model."""
    scenario = await _get_or_404(scenario_id, db, current_user.id)
    if scenario.status not in ("world_compiled", "agents_generated", "ready"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"World must be compiled first (current status: {scenario.status})",
        )

    scenario.status = "generating_agents"
    await db.commit()

    background_tasks.add_task(_generate_agents_task, scenario_id, count)
    return {"status": "generating_agents", "scenario_id": str(scenario_id)}


# ── Background task helpers ────────────────────────────────────────────────

async def _compile_world_task(scenario_id: uuid.UUID, source_text: str) -> None:
    from app.dependencies import get_session_factory
    factory = get_session_factory()
    async with factory() as db:
        scenario_result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
        scenario = scenario_result.scalars().first()
        if not scenario:
            return
        try:
            await compile_world(source_text, scenario_id, db, client=GeminiClient())
            scenario.status = "world_compiled"
        except Exception as exc:
            logger.error("World compilation failed for %s: %s", scenario_id, exc)
            scenario.status = "draft"
        await db.commit()


async def _generate_agents_task(scenario_id: uuid.UUID, count: int) -> None:
    from app.dependencies import get_session_factory
    from app.models.world import WorldModel
    factory = get_session_factory()
    async with factory() as db:
        scenario_result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
        scenario = scenario_result.scalars().first()
        world_result = await db.execute(select(WorldModel).where(WorldModel.scenario_id == scenario_id))
        world = world_result.scalars().first()
        if not scenario or not world:
            return
        try:
            await generate_agents(world, scenario_id, count=count, db=db, client=GeminiClient())
            scenario.status = "agents_generated"
        except Exception as exc:
            logger.error("Agent generation failed for %s: %s", scenario_id, exc)
            scenario.status = "world_compiled"
        await db.commit()


async def _get_or_404(
    scenario_id: uuid.UUID,
    db: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> Scenario:
    stmt = select(Scenario).where(Scenario.id == scenario_id)
    if user_id is not None:
        stmt = stmt.where(Scenario.user_id == user_id)
    result = await db.execute(stmt)
    scenario = result.scalars().first()
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return scenario
