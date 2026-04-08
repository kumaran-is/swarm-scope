"""
Report worker: post-run report generation with tool-augmented Gemini calls.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini.client import GeminiClient
from app.gemini.reporting import generate_report_outline, generate_report_section
from app.models.agent import Agent
from app.models.report import Report
from app.models.simulation import SimulationRun, Tick

logger = logging.getLogger(__name__)


# ── Report tools ──────────────────────────────────────────────────────────────

async def _tool_query_tick_data(
    sim_id: Any,
    tick_start: int,
    tick_end: int,
    db: AsyncSession,
) -> dict:
    """Return events from ticks in [tick_start, tick_end]."""
    result = await db.execute(
        select(Tick).where(
            Tick.simulation_run_id == sim_id,
            Tick.tick_number >= tick_start,
            Tick.tick_number <= tick_end,
        ).order_by(Tick.tick_number)
    )
    ticks = result.scalars().all()
    events = []
    for tick in ticks:
        tick_events = tick.events or []
        events.extend([{"tick": tick.tick_number, "event": e} for e in tick_events])
    return {"events": events[:50]}  # cap at 50


async def _tool_analyze_kpi_trajectory(
    sim_id: Any,
    kpi_name: str,
    db: AsyncSession,
) -> dict:
    """Compute trend, inflection points, and rate of change for a KPI."""
    result = await db.execute(
        select(Tick).where(Tick.simulation_run_id == sim_id).order_by(Tick.tick_number)
    )
    ticks = result.scalars().all()
    values: list[float] = []
    for tick in ticks:
        kpi_vals = tick.kpi_values or {}
        if kpi_name in kpi_vals:
            values.append(float(kpi_vals[kpi_name]))

    if not values:
        return {"kpi_name": kpi_name, "trend": "no_data", "values": []}

    trend = "stable"
    if len(values) >= 2:
        delta = values[-1] - values[0]
        if delta > 5:
            trend = "increasing"
        elif delta < -5:
            trend = "decreasing"

    # Find inflection points (sign change in delta)
    inflections = []
    for i in range(1, len(values) - 1):
        prev_delta = values[i] - values[i - 1]
        next_delta = values[i + 1] - values[i]
        if (prev_delta > 0 and next_delta < 0) or (prev_delta < 0 and next_delta > 0):
            inflections.append(i)

    rate_of_change = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0.0

    return {
        "kpi_name": kpi_name,
        "trend": trend,
        "start_value": values[0],
        "end_value": values[-1],
        "inflection_ticks": inflections,
        "rate_of_change": rate_of_change,
        "values": values[-10:],  # last 10 values
    }


async def _tool_compare_agent_outcomes(
    sim_id: Any,
    agent_ids: list[str],
    db: AsyncSession,
) -> dict:
    """Compare starting vs final state for each agent."""
    valid_ids = [__import__("uuid").UUID(aid) for aid in agent_ids if _is_valid_uuid(aid)]
    result = await db.execute(
        select(Agent).where(Agent.id.in_(valid_ids))
    )
    agents = result.scalars().all()
    outcomes = []
    for agent in agents:
        resources = agent.resources or {}
        outcomes.append({
            "agent_id": str(agent.id),
            "name": agent.name,
            "role": agent.role,
            "final_resources": resources,
            "goals": (agent.goals or [])[:3],
            "activation_score": agent.activation_score,
        })
    return {"outcomes": outcomes}


async def _tool_interview_agent(
    sim_id: Any,
    agent_id: str,
    question: str,
    db: AsyncSession,
    client: GeminiClient,
) -> dict:
    """Make a Gemini call with agent profile to answer a question in-character."""
    from app.gemini.prompts import AGENT_CHAT_PROMPT

    if not _is_valid_uuid(agent_id):
        return {"error": "Invalid agent ID"}

    result = await db.execute(
        select(Agent).where(Agent.id == __import__("uuid").UUID(agent_id))
    )
    agent = result.scalars().first()
    if not agent:
        return {"error": "Agent not found"}

    personality = agent.personality or {}
    resources = agent.resources or {}
    prompt = AGENT_CHAT_PROMPT.format(
        agent_name=agent.name,
        agent_role=agent.role or "unknown",
        scenario_name="the simulation",
        faction=agent.faction or "none",
        personality_summary=str(personality),
        goals_summary=str((agent.goals or [])[:2]),
        influence=resources.get("influence", 50),
        capital=resources.get("capital", 50),
        information=resources.get("information", 50),
        status=agent.status,
        current_tick=0,
        world_state_summary="",
        relevant_memories="",
        recent_actions="",
        user_message=question,
    )
    try:
        response = await client.extract_structured(prompt=prompt, response_schema=str, purpose="interview_agent")
        return {"agent_name": agent.name, "response": str(response.text)}
    except Exception as exc:
        logger.error("Interview agent %s failed: %s", agent_id, exc)
        return {"error": str(exc)}


async def _tool_find_causal_chain(
    sim_id: Any,
    event_description: str,
    db: AsyncSession,
) -> dict:
    """Search tick events for cause-effect sequences related to the event."""
    result = await db.execute(
        select(Tick).where(Tick.simulation_run_id == sim_id).order_by(Tick.tick_number)
    )
    ticks = result.scalars().all()
    related: list[dict] = []
    keywords = event_description.lower().split()[:5]
    for tick in ticks:
        for event in (tick.events or []):
            event_str = str(event).lower()
            if any(kw in event_str for kw in keywords):
                related.append({"tick": tick.tick_number, "event": event})
                if len(related) >= 10:
                    break
        if len(related) >= 10:
            break
    return {"causal_chain": related}


def _is_valid_uuid(val: str) -> bool:
    try:
        __import__("uuid").UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


# ── Main report generator ─────────────────────────────────────────────────────

async def generate_report_background(
    simulation_run: SimulationRun,
    scenario_name: str,
    domain: str,
    db: AsyncSession,
    client: GeminiClient | None = None,
) -> Report:
    """
    Generate a full post-simulation report using tool-augmented Gemini calls.
    """
    gemini = client or GeminiClient()
    sim_id = simulation_run.id
    tool_usage_log: list[dict] = []

    try:
        # 1. Generate outline
        outline = await generate_report_outline(
            scenario_name=scenario_name,
            domain=domain,
            ticks_completed=simulation_run.current_tick,
            outcome_summary=f"Simulation completed {simulation_run.current_tick} ticks",
            key_events_summary="See tick event log",
            client=gemini,
        )

        # 2. Per-section generation with tool augmentation
        sections_text: list[str] = []
        for section_idx, section in enumerate(outline):
            title = section.get("title", f"Section {section_idx + 1}")
            purpose = section.get("purpose", "")
            tools_to_use = section.get("tools_to_use", [])

            # Execute relevant tools for this section
            tool_context_parts: list[str] = []
            for tool_name in (tools_to_use[:3] if tools_to_use else []):
                tool_result: dict = {}
                ts = datetime.now(UTC).isoformat()

                if tool_name == "analyze_kpi_trajectory":
                    # Find KPI name from section title keywords
                    kpi_name = title.lower().replace(" ", "_")
                    tool_result = await _tool_analyze_kpi_trajectory(sim_id, kpi_name, db)
                elif tool_name == "query_tick_data":
                    tool_result = await _tool_query_tick_data(
                        sim_id, 0, simulation_run.current_tick, db
                    )
                elif tool_name == "interview_agent":
                    # Interview most active agent in this scenario
                    agents_result = await db.execute(
                        select(Agent).where(Agent.scenario_id == simulation_run.scenario_id)
                        .order_by(Agent.activation_score.desc()).limit(1)
                    )
                    top_agent = agents_result.scalars().first()
                    if top_agent:
                        tool_result = await _tool_interview_agent(
                            sim_id, str(top_agent.id), f"What happened during {title}?", db, gemini
                        )
                elif tool_name == "compare_agent_outcomes":
                    agents_result = await db.execute(
                        select(Agent.id).where(Agent.scenario_id == simulation_run.scenario_id).limit(5)
                    )
                    ids = [str(r) for r in agents_result.scalars().all()]
                    tool_result = await _tool_compare_agent_outcomes(sim_id, ids, db)
                elif tool_name == "find_causal_chain":
                    tool_result = await _tool_find_causal_chain(sim_id, title, db)

                if tool_result:
                    import json
                    summary = json.dumps(tool_result)[:500]
                    tool_usage_log.append({
                        "section_index": section_idx,
                        "tool_name": tool_name,
                        "tool_input": {"title": title},
                        "tool_output_summary": summary,
                        "timestamp": ts,
                    })
                    tool_context_parts.append(f"[Tool: {tool_name}]\n{summary}")

            tool_context = "\n\n".join(tool_context_parts)
            section_data = (
                f"Simulation: {scenario_name}, ticks: {simulation_run.current_tick}\n\n"
                f"{tool_context}"
            ) if tool_context else f"Simulation: {scenario_name}, ticks: {simulation_run.current_tick}"

            text = await generate_report_section(
                section_title=title,
                section_purpose=purpose,
                section_data=section_data,
                client=gemini,
            )
            sections_text.append(f"## {title}\n\n{text}")

        narrative = "\n\n".join(sections_text)

        # 3. Save report
        report = Report(
            simulation_run_id=sim_id,
            executive_summary=sections_text[0] if sections_text else "",
            narrative=narrative,
            timeline=[],
            influence_graph={"nodes": [], "edges": []},
            key_findings=[],
            kpi_trajectories={},
            tool_usage_log=tool_usage_log,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        logger.info(
            "Report generated for simulation %s (%d sections, %d tool calls)",
            sim_id, len(sections_text), len(tool_usage_log),
        )
        return report

    except Exception as exc:
        logger.error("Report generation failed for simulation %s: %s", sim_id, exc)
        raise
