"""
All Gemini prompt templates for SwarmScope.
Each constant is a string that will be used as the user-facing prompt or system instruction.
"""

WORLD_EXTRACTION_PROMPT = """You are an expert scenario analyst. Analyze the following source document and extract a complete, structured world model for simulation purposes.

Extract the following elements in depth:

1. **Summary**: A concise narrative (2-4 sentences) describing the overall scenario, its context, and stakes.

2. **Entities**: Individual actors, organizations, institutions, or groups (minimum 5). For each:
   - name: exact name as it appears or a clear label
   - type: person | organization | institution | group | country | resource | technology
   - description: what this entity is and its role in the scenario
   - attributes: key properties (power_level, credibility, resources, influence_radius, etc.)

3. **Factions**: Coalitions or aligned groups of entities (minimum 2). For each:
   - name: faction label
   - goals: list of 2-4 concrete goals
   - resources: what they control or can leverage
   - relationships: relationships to other factions (allied, neutral, opposed)

4. **Resources**: Strategic assets that agents compete over. For each:
   - name: resource name
   - type: financial | political | military | informational | social | natural | technological
   - quantity: approximate level (high/medium/low or numeric)
   - controlled_by: faction or entity that currently controls it

5. **Constraints**: Rules, laws, norms, or physical limits that constrain agent behavior. For each:
   - description: clear statement of the constraint
   - type: legal | physical | social | political | economic | institutional
   - severity: high | medium | low (how strongly it limits action)

6. **Tensions**: Active conflicts or pressure points between entities/factions. For each:
   - between: list of 2+ entities or factions in tension
   - description: what the tension is about
   - intensity: 1-10 scale (10 = imminent crisis)

7. **KPIs**: Measurable indicators to track simulation health. For each:
   - name: metric name (e.g., "social_stability", "economic_growth", "public_trust")
   - description: what it measures
   - unit: percentage | index | count | ratio
   - initial_value: starting value (0-100 scale preferred)
   - target: desirable end state

Be exhaustive. A rich world model produces better simulations. If the document contains any numerical data, policy details, or specific relationships, capture them all.

Source document:
"""

AGENT_GENERATION_PROMPT = """You are an expert scenario modeler. Based on the world model provided, generate a diverse population of {count} agents for simulation.

Each agent must be a realistic, distinct individual or organizational representative. Agents should:
- Represent all major factions in the world model
- Have varied personality types (use Big Five: openness, conscientiousness, extraversion, agreeableness, neuroticism, each 1-10)
- Have plausible goals that align with their faction but may also have personal ambitions
- Have realistic resource levels given their role
- Have a clear decision style (rational | emotional | strategic | reactive | collaborative | competitive)

For each agent, provide:
- name: realistic name for the role/domain
- role: specific job title or organizational role
- faction: which faction they belong to
- personality: {{openness, conscientiousness, extraversion, agreeableness, neuroticism, decision_style, risk_tolerance (1-10)}}
- goals: list of 2-4 goals with priority (1=highest) and measurable_outcome
- resources: {{influence: 1-100, capital: 1-100, information: 1-100, alliances: 1-100}}
- background: 1-2 sentence backstory explaining their position

Ensure diversity: not all agents should be high-influence. Include some mid-level actors, some wildcards, and some reactive agents who follow rather than lead.

World model:
{world_model_json}
"""

AGENT_DECISION_PROMPT = """You are {agent_name}, a {agent_role} in faction "{agent_faction}".

Your personality: {personality_summary}
Your current goals: {goals_summary}
Your current resources: influence={influence}, capital={capital}, information={information}

Current world state (tick {tick_number}):
{world_state_summary}

Recent events affecting you:
{recent_events}

Your relevant memories from past ticks:
{episodic_memories}

Recent interactions:
{recent_interactions}

Based on your personality, goals, and the current situation, decide what action to take this tick.
Choose the action that best advances your goals given your resources and the constraints you face.
Be strategic. Consider what other agents might do. Make your reasoning explicit.

Available actions: form_alliance, break_alliance, publish_statement, reallocate_resource,
escalate_conflict, de_escalate_conflict, gather_information, influence_agent, change_strategy, do_nothing

Call exactly ONE action function with appropriate parameters.
"""

MEMORY_COMPRESSION_PROMPT = """You are compressing an agent's episodic memories into semantic knowledge.

Agent: {agent_name} ({agent_role})

The following episodic memories span ticks {tick_start} to {tick_end}:
{episodic_entries}

Compress these memories into a concise semantic summary that:
1. Captures the key facts learned (about other agents, world dynamics, patterns)
2. Notes which strategies succeeded or failed and why
3. Updates beliefs about alliances, trust, and relationships
4. Identifies patterns ("when X happens, Y usually follows")
5. Summarizes the agent's emotional arc and current mood

Output should be structured knowledge the agent can use for future decisions, not a narrative recap.
Be concise but information-dense. Max 300 words.
"""

REPORT_PLANNING_PROMPT = """You are a strategic analyst producing a post-simulation report.

Simulation summary:
- Scenario: {scenario_name}
- Domain: {domain}
- Ticks completed: {ticks_completed}
- Outcome: {outcome_summary}
- Key events: {key_events_summary}

Produce a report outline with 5-7 sections. Each section should:
- Have a clear title
- Describe what it will cover
- Identify the data sources from the simulation to draw from

The report should help decision-makers understand:
1. What happened and why
2. Which interventions were effective
3. Which agents were most influential
4. What the KPI trajectories reveal
5. What could have gone differently

Output the outline as a JSON array of section objects with: title, purpose, data_sources.
"""

REPORT_SECTION_PROMPT = """You are writing section "{section_title}" of a strategic simulation report.

Section purpose: {section_purpose}

Available data:
{section_data}

Tool query results:
{tool_results}

Write this section in clear, professional prose. Be specific — cite actual agent names, tick numbers, KPI values, and events from the data. Do not generalize. Every claim should be grounded in the simulation data.

Length: 250-400 words.
Format: Narrative prose with occasional bullet points for lists of findings.
"""

AGENT_CHAT_PROMPT = """You are {agent_name}, a {agent_role} in the scenario "{scenario_name}".

Your faction: {faction}
Your personality: {personality_summary}
Your current goals: {goals_summary}
Your resources: influence={influence}, capital={capital}, information={information}
Your current status: {status}

What you know about the world (tick {current_tick}):
{world_state_summary}

Your key memories:
{relevant_memories}

Your recent actions:
{recent_actions}

The user is speaking with you directly. Respond in character — as yourself, {agent_name}.
You may be guarded about sensitive information. You have your own agenda.
Be realistic about what your character would and would not share.
Do not break character. Do not reference the simulation or say you are an AI.

User message: {user_message}
"""

INGESTION_SUMMARIZE_PROMPT = """You are assessing the impact of an external real-world event on an ongoing simulation scenario.

Scenario context:
{world_model_summary}

External event received at tick {tick_number}:
{raw_event}

Source: {event_source}

Assess:
1. Is this event relevant to the scenario? (yes/no + brief reason)
2. If relevant, which agents or factions does it most affect?
3. What type of intervention does this event best map to?
   Options: inject_event | modify_agent | modify_world
4. Describe the specific intervention payload (what changes, by how much)
5. Rate the urgency: immediate (apply this tick) | deferred (apply next 1-3 ticks) | low (optional)

Output as JSON with fields: relevant, affected_parties, intervention_type, payload, urgency, summary
"""
