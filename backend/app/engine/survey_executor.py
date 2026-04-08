"""
Survey executor: batch agent surveys via Gemini.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.gemini.client import GeminiClient
from app.gemini.prompts import AGENT_CHAT_PROMPT
from app.models.agent import Agent
from app.models.ingestion import Survey

logger = logging.getLogger(__name__)


async def execute_survey(
    survey: Survey,
    agents: list[Agent],
    world_state: dict,
    scenario_name: str,
    current_tick: int,
    client: GeminiClient | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """
    Ask a survey question to specified agents and collect responses.
    Returns aggregated responses dict.
    """
    import asyncio

    gemini = client or GeminiClient()
    target_ids = set(str(tid) for tid in survey.target_agent_ids)
    target_agents = [a for a in agents if str(a.id) in target_ids]

    if not target_agents:
        logger.warning("No target agents found for survey %s", survey.id)
        return {}

    async def ask_agent(agent: Agent) -> tuple[str, str]:
        personality = agent.personality or {}
        personality_summary = (
            f"decision_style={personality.get('decision_style', 'rational')}, "
            f"risk_tolerance={personality.get('risk_tolerance', 5)}"
        )
        goals = agent.goals or []
        goals_summary = "; ".join(g.get("description", "") for g in goals[:2] if isinstance(g, dict))
        resources = agent.resources or {}

        prompt = AGENT_CHAT_PROMPT.format(
            agent_name=agent.name,
            agent_role=agent.role or "unknown",
            scenario_name=scenario_name,
            faction=agent.faction or "none",
            personality_summary=personality_summary,
            goals_summary=goals_summary,
            influence=resources.get("influence", 50),
            capital=resources.get("capital", 50),
            information=resources.get("information", 50),
            status=agent.status,
            current_tick=current_tick,
            world_state_summary=world_state.get("summary", ""),
            relevant_memories="",
            recent_actions="",
            user_message=survey.question,
        )

        try:
            response = await gemini.extract_structured(
                prompt=prompt,
                response_schema=str,
                purpose=f"survey:{agent.name}",
            )
            return str(agent.id), response.text.strip('"').strip()
        except Exception as exc:
            logger.error("Survey response failed for agent %s: %s", agent.name, exc)
            return str(agent.id), f"[Error: {exc}]"

    tasks = [ask_agent(agent) for agent in target_agents]
    results = await asyncio.gather(*tasks)
    responses = dict(results)

    # Update survey record
    if db:
        survey.responses = responses
        await db.commit()

    logger.info(
        "Survey %s complete: %d/%d agents responded",
        survey.id,
        len([v for v in responses.values() if not v.startswith("[Error")]),
        len(target_agents),
    )
    return responses
