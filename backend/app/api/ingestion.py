"""Ingestion source CRUD and webhook receiver endpoints."""

import hashlib
import hmac
import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.ingestion import IngestedEvent, IngestionSource
from app.models.user import User

logger = logging.getLogger(__name__)

# Router for authenticated CRUD endpoints
router = APIRouter(tags=["ingestion"])

# Router for webhook receiver (no JWT — uses HMAC auth)
webhook_router = APIRouter(tags=["webhooks"])


class IngestionSourceCreate(BaseModel):
    name: str
    source_type: str  # 'webhook' | 'scheduled_pull'
    config: dict = {}
    mapping_rules: dict = {}
    rate_limit_per_minute: int = 5


class IngestionSourceResponse(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    name: str
    source_type: str
    config: dict | None
    mapping_rules: dict | None
    rate_limit_per_minute: int | None
    webhook_secret: str | None
    is_active: bool


class IngestedEventResponse(BaseModel):
    id: uuid.UUID
    simulation_run_id: uuid.UUID | None
    ingestion_source_id: uuid.UUID
    raw_payload: dict
    processed_intervention: dict | None
    intervention_id: uuid.UUID | None
    status: str
    created_at: str


# ── CRUD endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/scenarios/{scenario_id}/ingestion-sources",
    response_model=IngestionSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    scenario_id: uuid.UUID,
    body: IngestionSourceCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> IngestionSource:
    secret = secrets.token_hex(32) if body.source_type == "webhook" else None
    source = IngestionSource(
        scenario_id=scenario_id,
        name=body.name,
        source_type=body.source_type,
        config=body.config,
        mapping_rules=body.mapping_rules,
        rate_limit_per_minute=body.rate_limit_per_minute,
        webhook_secret=secret,
        is_active=True,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/scenarios/{scenario_id}/ingestion-sources", response_model=list[IngestionSourceResponse])
async def list_sources(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[IngestionSource]:
    result = await db.execute(
        select(IngestionSource).where(IngestionSource.scenario_id == scenario_id)
    )
    return list(result.scalars().all())


@router.put("/scenarios/{scenario_id}/ingestion-sources/{source_id}", response_model=IngestionSourceResponse)
async def update_source(
    scenario_id: uuid.UUID,
    source_id: uuid.UUID,
    body: IngestionSourceCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> IngestionSource:
    source = await _get_source_or_404(source_id, scenario_id, db)
    source.name = body.name
    source.config = body.config
    source.mapping_rules = body.mapping_rules
    source.rate_limit_per_minute = body.rate_limit_per_minute
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/scenarios/{scenario_id}/ingestion-sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    scenario_id: uuid.UUID,
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    source = await _get_source_or_404(source_id, scenario_id, db)
    await db.delete(source)
    await db.commit()


@router.post("/scenarios/{scenario_id}/ingestion-sources/{source_id}/test")
async def test_source(
    scenario_id: uuid.UUID,
    source_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Dry-run the ingestion pipeline without creating records."""
    source = await _get_source_or_404(source_id, scenario_id, db)
    mapping_rules = source.mapping_rules or {}
    event_field = mapping_rules.get("event_field", "description")
    event_text = _extract_field(payload, event_field)

    return {
        "dry_run": True,
        "source_name": source.name,
        "extracted_event": event_text,
        "would_create_intervention": {
            "type": "inject_event",
            "payload": {"description": event_text, "source": source.name},
        },
    }


@router.get("/simulations/{sim_id}/ingested-events", response_model=list[IngestedEventResponse])
async def list_ingested_events(
    sim_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[IngestedEvent]:
    result = await db.execute(
        select(IngestedEvent).where(IngestedEvent.simulation_run_id == sim_id)
        .order_by(IngestedEvent.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())


# ── Webhook receiver (no JWT) ─────────────────────────────────────────────────

@webhook_router.post("/webhooks/ingest/{source_id}")
async def receive_webhook(
    source_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive an external webhook payload and ingest it as an event."""
    body = await request.body()
    signature_header = request.headers.get("X-Webhook-Signature", "")

    result = await db.execute(select(IngestionSource).where(IngestionSource.id == source_id))
    source = result.scalars().first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion source not found")

    if not source.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Source is inactive")

    # HMAC verification
    if source.webhook_secret:
        expected = hmac.new(
            source.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature_header):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    try:
        import json
        payload = json.loads(body)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    mapping_rules = source.mapping_rules or {}
    event_field = mapping_rules.get("event_field", "description")
    event_text = _extract_field(payload, event_field)

    event = IngestedEvent(
        ingestion_source_id=source_id,
        simulation_run_id=None,  # Will be linked when ingestion worker picks it up
        raw_payload=payload,
        processed_intervention={"description": event_text, "source": str(source_id)},
        status="pending",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info("Webhook received for source %s, event %s", source_id, event.id)
    return {"event_id": str(event.id), "status": "received"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_field(payload: dict, field_path: str) -> str:
    """Simple dot-notation field extractor."""
    if not field_path:
        return str(payload)
    parts = field_path.split(".")
    val = payload
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part, "")
        else:
            return str(val)
    return str(val)


async def _get_source_or_404(
    source_id: uuid.UUID, scenario_id: uuid.UUID, db: AsyncSession
) -> IngestionSource:
    result = await db.execute(
        select(IngestionSource).where(
            IngestionSource.id == source_id,
            IngestionSource.scenario_id == scenario_id,
        )
    )
    source = result.scalars().first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion source not found")
    return source
