"""
Tool-augmented report section generation using Gemini.
"""

import json
import logging

from app.gemini.client import GeminiClient
from app.gemini.prompts import REPORT_PLANNING_PROMPT, REPORT_SECTION_PROMPT

logger = logging.getLogger(__name__)


async def generate_report_outline(
    scenario_name: str,
    domain: str,
    ticks_completed: int,
    outcome_summary: str,
    key_events_summary: str,
    client: GeminiClient | None = None,
) -> list[dict]:
    """
    Generate a report outline with sections from simulation summary.
    Returns a list of section dicts: {title, purpose, data_sources}.
    """
    gemini = client or GeminiClient()

    prompt = REPORT_PLANNING_PROMPT.format(
        scenario_name=scenario_name,
        domain=domain,
        ticks_completed=ticks_completed,
        outcome_summary=outcome_summary,
        key_events_summary=key_events_summary,
    )

    class ReportSection:
        pass

    from pydantic import BaseModel

    class SectionOutline(BaseModel):
        title: str
        purpose: str
        data_sources: list[str]

    class ReportOutline(BaseModel):
        sections: list[SectionOutline]

    try:
        response = await gemini.extract_structured(
            prompt=prompt,
            response_schema=ReportOutline,
            purpose="report_planning",
        )
        data = json.loads(response.text)
        outline = ReportOutline.model_validate(data)
        return [s.model_dump() for s in outline.sections]

    except Exception as exc:
        logger.error("Report outline generation failed: %s", exc)
        # Return a minimal default outline
        return [
            {"title": "Executive Summary", "purpose": "Overview of simulation outcomes", "data_sources": ["ticks", "kpis"]},
            {"title": "Key Events", "purpose": "Significant events by tick", "data_sources": ["events"]},
            {"title": "KPI Trajectories", "purpose": "How metrics evolved", "data_sources": ["kpi_values"]},
            {"title": "Influence Analysis", "purpose": "Agent influence network", "data_sources": ["influence_edges"]},
            {"title": "Conclusions", "purpose": "What this simulation reveals", "data_sources": ["all"]},
        ]


async def generate_report_section(
    section_title: str,
    section_purpose: str,
    section_data: str,
    tool_results: str = "",
    client: GeminiClient | None = None,
) -> str:
    """
    Generate prose for one report section given data and tool query results.
    Returns narrative text.
    """
    gemini = client or GeminiClient()

    prompt = REPORT_SECTION_PROMPT.format(
        section_title=section_title,
        section_purpose=section_purpose,
        section_data=section_data,
        tool_results=tool_results or "No additional tool results.",
    )

    try:
        response = await gemini.extract_structured(
            prompt=prompt,
            response_schema=str,
            purpose=f"report_section:{section_title}",
        )
        return str(response.text).strip('"').strip()

    except Exception as exc:
        logger.error("Report section generation failed for '%s': %s", section_title, exc)
        return f"[Section generation failed: {exc}]"
