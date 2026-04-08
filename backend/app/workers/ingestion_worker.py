"""
Ingestion worker: scheduled pull background worker for external data sources.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.ingestion_handler import IngestionHandler
from app.gemini.client import GeminiClient
from app.models.ingestion import IngestedEvent, IngestionSource

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.handler = IngestionHandler(client=client)

    async def check_sources(
        self,
        simulation_run_id: UUID,
        tick_number: int,
        world_state_summary: str,
        db: AsyncSession,
    ) -> int:
        """
        Check all active ingestion sources for new events.
        Returns the number of events processed.
        """
        # Get unprocessed events for active sources
        result = await db.execute(
            select(IngestedEvent).where(
                IngestedEvent.simulation_run_id == simulation_run_id,
                IngestedEvent.status == "pending",
            ).limit(20)  # MAX_INGESTED_EVENTS_PER_TICK
        )
        events = list(result.scalars().all())

        processed = 0
        for event in events:
            source_result = await db.execute(
                select(IngestionSource).where(IngestionSource.id == event.ingestion_source_id)
            )
            source = source_result.scalars().first()
            if source and source.is_active:
                intervention = await self.handler.process_event(
                    event=event,
                    source=source,
                    simulation_run_id=simulation_run_id,
                    world_state_summary=world_state_summary,
                    tick_number=tick_number,
                    db=db,
                )
                if intervention:
                    processed += 1

        logger.debug(
            "Ingestion check at tick %d: %d/%d events processed",
            tick_number, processed, len(events)
        )
        return processed
