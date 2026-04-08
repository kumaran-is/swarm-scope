"""
World compiler: converts source document text into a structured WorldModel via Gemini.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini.client import GeminiClient
from app.gemini.extraction import WorldExtraction, extract_world_model
from app.models.world import WorldModel

logger = logging.getLogger(__name__)


async def compile_world(
    source_text: str,
    scenario_id: UUID,
    db: AsyncSession,
    client: GeminiClient | None = None,
) -> WorldModel:
    """
    Extract a structured WorldModel from raw source text using Gemini.

    Validation: requires at least 2 entities, 1 tension, and 1 KPI.
    Retries once with a stricter prompt if validation fails.
    Persists the result to the world_models table.
    """
    extraction = await extract_world_model(source_text, client=client)

    # Validate — retry if output is too sparse
    if not _is_valid(extraction):
        logger.warning(
            "World extraction too sparse (entities=%d, tensions=%d, kpis=%d) — retrying",
            len(extraction.entities),
            len(extraction.tensions),
            len(extraction.kpis),
        )
        richer_text = (
            "IMPORTANT: Be exhaustive. Extract ALL entities, factions, tensions, and KPIs. "
            "Minimum: 5 entities, 2 factions, 2 tensions, 3 KPIs.\n\n" + source_text
        )
        extraction = await extract_world_model(richer_text, client=client)
        if not _is_valid(extraction):
            logger.warning(
                "World extraction still sparse after retry — proceeding with partial result"
            )

    # Persist to DB
    world = WorldModel(
        scenario_id=scenario_id,
        summary=extraction.summary,
        entities=[e.model_dump() for e in extraction.entities],
        factions=[f.model_dump() for f in extraction.factions],
        resources=[r.model_dump() for r in extraction.resources],
        constraints=[c.model_dump() for c in extraction.constraints],
        tensions=[t.model_dump() for t in extraction.tensions],
        kpis=[k.model_dump() for k in extraction.kpis],
        raw_extraction=extraction.model_dump(),
    )
    db.add(world)
    await db.commit()
    await db.refresh(world)

    logger.info(
        "WorldModel compiled and saved (scenario=%s, entities=%d, factions=%d, kpis=%d)",
        scenario_id,
        len(extraction.entities),
        len(extraction.factions),
        len(extraction.kpis),
    )
    return world


def _is_valid(extraction: WorldExtraction) -> bool:
    return (
        len(extraction.entities) >= 2
        and len(extraction.tensions) >= 1
        and len(extraction.kpis) >= 1
    )
