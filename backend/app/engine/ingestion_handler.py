"""
Ingestion handler: process external data events into simulation interventions.
"""

import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini.client import GeminiClient
from app.gemini.prompts import INGESTION_SUMMARIZE_PROMPT
from app.models.ingestion import IngestedEvent, IngestionSource
from app.models.intervention import Intervention

logger = logging.getLogger(__name__)


class IngestionHandler:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    async def process_event(
        self,
        event: IngestedEvent,
        source: IngestionSource,
        simulation_run_id: UUID,
        world_state_summary: str,
        tick_number: int,
        db: AsyncSession,
    ) -> Intervention | None:
        """
        Use Gemini to assess whether a raw ingested event is relevant and should
        become an intervention. Returns a new Intervention if relevant, None otherwise.
        """
        raw_payload = event.raw_payload or {}
        raw_text = json.dumps(raw_payload)

        prompt = INGESTION_SUMMARIZE_PROMPT.format(
            world_model_summary=world_state_summary,
            tick_number=tick_number,
            raw_event=raw_text,
            event_source=source.name,
        )

        try:
            from pydantic import BaseModel

            class IngestionAssessment(BaseModel):
                relevant: bool
                affected_parties: list[str]
                intervention_type: str
                payload: dict
                urgency: str
                summary: str

            response = await self.client.extract_structured(
                prompt=prompt,
                response_schema=IngestionAssessment,
                purpose="ingestion_assessment",
            )
            assessment = IngestionAssessment.model_validate(json.loads(response.text))

            if not assessment.relevant:
                event.status = "rejected"
                event.rejection_reason = "Not relevant to scenario"
                await db.commit()
                return None

            # Create intervention from assessment
            intervention = Intervention(
                simulation_run_id=simulation_run_id,
                type=assessment.intervention_type,
                payload=assessment.payload,
                description=assessment.summary,
                target_tick=None,  # apply at next tick
                status="pending",
            )
            db.add(intervention)
            event.status = "processed"
            event.intervention_id = intervention.id
            event.processed_intervention = assessment.model_dump()
            await db.commit()
            await db.refresh(intervention)

            logger.info(
                "Ingested event %s → intervention %s (%s)",
                event.id,
                intervention.id,
                assessment.intervention_type,
            )
            return intervention

        except Exception as exc:
            logger.error("Ingestion processing failed for event %s: %s", event.id, exc)
            event.status = "rejected"
            event.rejection_reason = f"Processing error: {exc}"
            await db.commit()
            return None
