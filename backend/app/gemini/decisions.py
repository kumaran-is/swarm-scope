"""
Agent decision resolution via Gemini function calling.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from google.genai import types

from app.gemini.client import GeminiClient
from app.gemini.prompts import AGENT_DECISION_PROMPT

logger = logging.getLogger(__name__)


# ── Function declarations for all 10 agent actions ──────────────────────────

AGENT_ACTIONS = [
    types.FunctionDeclaration(
        name="form_alliance",
        description="Propose a formal alliance with another agent, agreeing to cooperate toward shared goals.",
        parameters={
            "type": "object",
            "properties": {
                "target_agent_id": {"type": "string", "description": "ID of the agent to ally with"},
                "terms": {"type": "string", "description": "Terms and expectations of the alliance"},
                "offered_resources": {"type": "array", "items": {"type": "string"}, "description": "Resources offered as part of the alliance"},
            },
            "required": ["target_agent_id", "terms"],
        },
    ),
    types.FunctionDeclaration(
        name="break_alliance",
        description="Dissolve an existing alliance with another agent.",
        parameters={
            "type": "object",
            "properties": {
                "target_agent_id": {"type": "string", "description": "ID of the agent to break alliance with"},
                "reason": {"type": "string", "description": "Reason for breaking the alliance"},
            },
            "required": ["target_agent_id", "reason"],
        },
    ),
    types.FunctionDeclaration(
        name="publish_statement",
        description="Publish a public statement, announcement, or communication to an audience.",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The statement content"},
                "audience": {"type": "string", "description": "Target audience (public, faction, specific_agent, etc.)"},
                "tone": {"type": "string", "description": "Tone: conciliatory | aggressive | neutral | diplomatic | urgent"},
            },
            "required": ["content", "audience", "tone"],
        },
    ),
    types.FunctionDeclaration(
        name="reallocate_resource",
        description="Move or redistribute resources between parties.",
        parameters={
            "type": "object",
            "properties": {
                "resource_type": {"type": "string", "description": "Type of resource: influence | capital | information | alliances"},
                "amount": {"type": "number", "description": "Amount to transfer (1-100 scale)"},
                "from_party": {"type": "string", "description": "Source party (self or agent_id)"},
                "to_party": {"type": "string", "description": "Destination party (agent_id or faction)"},
            },
            "required": ["resource_type", "amount", "from_party", "to_party"],
        },
    ),
    types.FunctionDeclaration(
        name="escalate_conflict",
        description="Increase pressure or conflict with a target agent or faction.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target agent or faction ID"},
                "method": {"type": "string", "description": "Method: sanctions | public_attack | legal_action | military | propaganda | sabotage"},
                "intensity": {"type": "number", "description": "Intensity 1-10"},
            },
            "required": ["target", "method", "intensity"],
        },
    ),
    types.FunctionDeclaration(
        name="de_escalate_conflict",
        description="Reduce tension or conflict with a target agent or faction.",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target agent or faction ID"},
                "concession": {"type": "string", "description": "What concession or gesture is offered to de-escalate"},
            },
            "required": ["target", "concession"],
        },
    ),
    types.FunctionDeclaration(
        name="gather_information",
        description="Attempt to gather intelligence or information about a topic or agent.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "What information to gather"},
                "method": {"type": "string", "description": "Method: surveillance | interview | research | network | media_monitoring"},
            },
            "required": ["topic", "method"],
        },
    ),
    types.FunctionDeclaration(
        name="influence_agent",
        description="Attempt to change another agent's behavior, beliefs, or goals.",
        parameters={
            "type": "object",
            "properties": {
                "target_agent_id": {"type": "string", "description": "ID of agent to influence"},
                "method": {"type": "string", "description": "Method: persuasion | bribery | coercion | propaganda | negotiation"},
                "goal": {"type": "string", "description": "Desired behavior change or outcome"},
            },
            "required": ["target_agent_id", "method", "goal"],
        },
    ),
    types.FunctionDeclaration(
        name="change_strategy",
        description="Shift the agent's overall approach or strategy.",
        parameters={
            "type": "object",
            "properties": {
                "new_strategy": {"type": "string", "description": "Description of the new strategic direction"},
                "reasoning": {"type": "string", "description": "Why this strategy change is warranted now"},
            },
            "required": ["new_strategy", "reasoning"],
        },
    ),
    types.FunctionDeclaration(
        name="do_nothing",
        description="Take no action this tick. Explicit inaction is a valid strategic choice.",
        parameters={
            "type": "object",
            "properties": {
                "reasoning": {"type": "string", "description": "Why inaction is the best choice this tick"},
            },
            "required": ["reasoning"],
        },
    ),
]


@dataclass
class AgentAction:
    action_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


async def get_agent_decision(
    agent_name: str,
    agent_role: str,
    agent_faction: str,
    personality: dict,
    goals: list,
    resources: dict,
    tick_number: int,
    world_state_summary: str,
    recent_events: str,
    episodic_memories: str,
    recent_interactions: str,
    client: GeminiClient | None = None,
) -> AgentAction:
    """
    Use Gemini function calling to resolve an agent's decision for this tick.
    Returns an AgentAction with the chosen action name and parameters.
    """
    gemini = client or GeminiClient()

    personality_summary = (
        f"openness={personality.get('openness', 5)}, "
        f"conscientiousness={personality.get('conscientiousness', 5)}, "
        f"extraversion={personality.get('extraversion', 5)}, "
        f"agreeableness={personality.get('agreeableness', 5)}, "
        f"neuroticism={personality.get('neuroticism', 5)}, "
        f"decision_style={personality.get('decision_style', 'rational')}, "
        f"risk_tolerance={personality.get('risk_tolerance', 5)}"
    )

    goals_summary = "; ".join(
        f"[P{g.get('priority', 1)}] {g.get('description', '')}"
        for g in goals[:3]
    )

    prompt = AGENT_DECISION_PROMPT.format(
        agent_name=agent_name,
        agent_role=agent_role,
        agent_faction=agent_faction,
        personality_summary=personality_summary,
        goals_summary=goals_summary,
        influence=resources.get("influence", 50),
        capital=resources.get("capital", 50),
        information=resources.get("information", 50),
        tick_number=tick_number,
        world_state_summary=world_state_summary,
        recent_events=recent_events,
        episodic_memories=episodic_memories,
        recent_interactions=recent_interactions,
    )

    try:
        response = await gemini.call_with_functions(
            prompt=prompt,
            function_declarations=AGENT_ACTIONS,
            purpose=f"agent_decision:{agent_name}",
        )

        # Parse function call from response
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    return AgentAction(
                        action_name=fc.name,
                        parameters=dict(fc.args) if fc.args else {},
                    )

        # If no function call returned, default to do_nothing
        logger.warning("Agent %s returned no function call — defaulting to do_nothing", agent_name)
        return AgentAction(action_name="do_nothing", parameters={"reasoning": "No decision returned"})

    except Exception as exc:
        logger.error("Agent decision failed for %s: %s", agent_name, exc)
        return AgentAction(action_name="do_nothing", parameters={"reasoning": f"Decision error: {exc}"})
