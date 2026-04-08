# SwarmScope — Scenario Simulation Lab: Complete Build Prompt

> **Purpose**: Copy this entire prompt into Claude Code to scaffold and build the full application.
> **Stack**: Angular 21 + Python 3.14 + FastAPI + Gemini + PostgreSQL + Redis
> **MVP Scope**: 1 source document, 1 scenario mode, 100 agents, 15 ticks, 3 intervention types, top 10 agents chat-enabled, final report + timeline + influence graph

---

## PROMPT START

You are building **SwarmScope** — a Scenario Simulation Lab that lets users upload a source document, compile a structured world model, generate an agent population, run a tick-based simulation with selective LLM activation, inject interventions, and produce an auditable forecasting report. This is NOT a social-media simulator. It is a general-purpose scenario engine for policy impact, organizational change, crisis planning, market/consumer response, and fiction/worldbuilding.

---

## 1. PROJECT STRUCTURE

Create a monorepo with this layout:

```
swarm-scope/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── backend/                          # Python 3.14 + FastAPI
│   ├── pyproject.toml                # Use uv or poetry — pin Python >=3.14
│   ├── alembic/                      # DB migrations
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, CORS, lifespan
│   │   ├── config.py                 # Pydantic Settings (env-based)
│   │   ├── dependencies.py           # Dependency injection (DB session, Redis, Gemini client)
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── scenario.py           # Scenario, ScenarioConfig
│   │   │   ├── world.py              # WorldModel, Entity, Faction, Resource, Constraint, Tension, KPI
│   │   │   ├── agent.py              # Agent, AgentProfile, AgentMemory
│   │   │   ├── simulation.py         # SimulationRun, Tick, TickEvent, Snapshot
│   │   │   ├── intervention.py       # Intervention, InterventionType
│   │   │   ├── report.py             # Report, ReportSection, TimelineEvent, InfluenceEdge
│   │   │   ├── user.py               # User model (JWT auth)
│   │   │   ├── ensemble.py           # EnsembleRun model
│   │   │   └── ingestion.py          # IngestionSource, IngestedEvent models
│   │   │
│   │   ├── schemas/                  # Pydantic v2 request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── scenario.py
│   │   │   ├── world.py
│   │   │   ├── agent.py
│   │   │   ├── simulation.py
│   │   │   ├── intervention.py
│   │   │   └── report.py
│   │   │
│   │   ├── api/                      # Route modules
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # Top-level APIRouter aggregating all sub-routers
│   │   │   ├── scenarios.py          # CRUD for scenarios + file upload
│   │   │   ├── world.py              # World model viewing + editing endpoints
│   │   │   ├── agents.py             # Agent population endpoints + chat
│   │   │   ├── simulation.py         # Start/pause/resume/stop + tick streaming
│   │   │   ├── interventions.py      # Create/fire interventions mid-simulation
│   │   │   ├── reports.py            # Generate + retrieve reports
│   │   │   └── ws.py                 # WebSocket endpoint for live dashboard streaming
│   │   │
│   │   ├── engine/                   # CORE SIMULATION ENGINE
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py       # Main tick loop — the heart of the system
│   │   │   ├── world_compiler.py     # Source doc → structured WorldModel via Gemini
│   │   │   ├── agent_generator.py    # WorldModel → Agent population via Gemini
│   │   │   ├── activation.py         # Selective activation: pick which agents invoke LLM this tick
│   │   │   ├── rule_engine.py        # Deterministic rule resolution (before LLM calls)
│   │   │   ├── decision_engine.py    # Gemini function-calling for agent decisions
│   │   │   ├── state_manager.py      # World state update + snapshot persistence
│   │   │   ├── memory_manager.py     # 3-layer memory: working / episodic / semantic
│   │   │   ├── intervention_handler.py  # Process God's-eye interventions
│   │   │   ├── event_log.py          # Append-only event sourcing log
│   │   │   ├── influence_tracker.py   # Track agent-to-agent influence edges per tick
│   │   │   ├── fork_manager.py        # Create forked simulation from tick snapshot
│   │   │   ├── survey_executor.py     # Batch agent surveys via Gemini
│   │   │   ├── determinism_auditor.py # Track where stochasticity entered
│   │   │   ├── ensemble_runner.py     # Orchestrate N parallel runs with different seeds
│   │   │   ├── ensemble_aggregator.py # Compute statistics across ensemble runs (numpy)
│   │   │   └── ingestion_handler.py   # Process external data → interventions
│   │   │
│   │   ├── gemini/                   # Gemini integration layer
│   │   │   ├── __init__.py
│   │   │   ├── client.py             # google-genai SDK wrapper, retry logic, rate limiting
│   │   │   ├── prompts.py            # All Gemini prompt templates (structured output schemas)
│   │   │   ├── extraction.py         # Structured output: extract entities/factions/goals/KPIs
│   │   │   ├── decisions.py          # Function calling: agent action resolution
│   │   │   ├── embeddings.py         # Embedding generation for memory retrieval
│   │   │   └── reporting.py          # Report narrative generation
│   │   │
│   │   ├── workers/                  # Background task workers
│   │   │   ├── __init__.py
│   │   │   ├── simulation_worker.py  # Runs the tick loop in background
│   │   │   ├── report_worker.py      # Post-run report generation
│   │   │   └── ingestion_worker.py   # Scheduled pull background worker for external data
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_parser.py        # PDF/DOCX/TXT/MD → plain text extraction
│   │       ├── determinism.py        # Seeded random, reproducibility helpers
│   │       └── serialization.py      # Snapshot serialization/deserialization
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_engine/
│       ├── test_api/
│       └── test_gemini/
│
├── frontend/                         # Angular 21
│   ├── angular.json
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── app/
│   │   │   ├── app.component.ts
│   │   │   ├── app.routes.ts
│   │   │   ├── app.config.ts
│   │   │   │
│   │   │   ├── core/                 # Singleton services, guards, interceptors
│   │   │   │   ├── services/
│   │   │   │   │   ├── api.service.ts            # HttpClient wrapper
│   │   │   │   │   ├── websocket.service.ts      # WebSocket connection manager
│   │   │   │   │   ├── scenario.service.ts
│   │   │   │   │   ├── simulation.service.ts
│   │   │   │   │   ├── intervention.service.ts
│   │   │   │   │   └── report.service.ts
│   │   │   │   ├── interceptors/
│   │   │   │   │   └── error.interceptor.ts
│   │   │   │   └── guards/
│   │   │   │       └── simulation-active.guard.ts
│   │   │   │
│   │   │   ├── shared/               # Shared standalone components, pipes, directives
│   │   │   │   ├── components/
│   │   │   │   │   ├── file-upload/
│   │   │   │   │   ├── agent-card/
│   │   │   │   │   ├── tick-timeline/
│   │   │   │   │   ├── kpi-gauge/
│   │   │   │   │   └── influence-graph/
│   │   │   │   └── pipes/
│   │   │   │       └── relative-time.pipe.ts
│   │   │   │
│   │   │   ├── features/             # Feature modules (lazy-loaded standalone components)
│   │   │   │   ├── scenario-intake/
│   │   │   │   │   ├── scenario-intake.component.ts    # Upload doc, name scenario, set params
│   │   │   │   │   └── scenario-intake.component.html
│   │   │   │   │
│   │   │   │   ├── world-editor/
│   │   │   │   │   ├── world-editor.component.ts       # View/edit extracted world model
│   │   │   │   │   └── world-editor.component.html
│   │   │   │   │
│   │   │   │   ├── simulation-control/
│   │   │   │   │   ├── simulation-control.component.ts # Start/pause/resume/stop controls
│   │   │   │   │   └── simulation-control.component.html
│   │   │   │   │
│   │   │   │   ├── live-dashboard/
│   │   │   │   │   ├── live-dashboard.component.ts     # Real-time world state via WebSocket
│   │   │   │   │   └── live-dashboard.component.html
│   │   │   │   │
│   │   │   │   ├── intervention-console/
│   │   │   │   │   ├── intervention-console.component.ts  # Fire interventions mid-simulation
│   │   │   │   │   └── intervention-console.component.html
│   │   │   │   │
│   │   │   │   ├── agent-chat/
│   │   │   │   │   ├── agent-chat.component.ts         # Chat with top 10 active agents
│   │   │   │   │   └── agent-chat.component.html
│   │   │   │   │
│   │   │   │   ├── report-viewer/
│   │   │   │   │   ├── report-viewer.component.ts      # Final report + timeline + influence graph
│   │   │   │   │   └── report-viewer.component.html
│   │   │   │   │
│   │   │   │   ├── ensemble-viewer/
│   │   │   │   │   ├── ensemble-viewer.component.ts    # Robustness gauge, KPI confidence bands, heatmap
│   │   │   │   │   └── ensemble-viewer.component.html
│   │   │   │   │
│   │   │   │   ├── scenario-library/
│   │   │   │   │   ├── scenario-library.component.ts   # Card grid, clone, filter, search
│   │   │   │   │   └── scenario-library.component.html
│   │   │   │   │
│   │   │   │   └── auth/
│   │   │   │       ├── login.component.ts
│   │   │   │       └── register.component.ts
│   │   │   │
│   │   │   └── state/                # Signal-based state management
│   │   │       ├── scenario.state.ts
│   │   │       ├── simulation.state.ts
│   │   │       ├── world.state.ts
│   │   │       └── agents.state.ts
│   │   │
│   │   ├── environments/
│   │   │   ├── environment.ts
│   │   │   └── environment.prod.ts
│   │   │
│   │   └── styles/
│   │       └── global.scss
│   │
│   └── e2e/
│
└── infra/
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── nginx.conf
```

---

## 2. DATABASE SCHEMA

Use PostgreSQL. Create these tables via Alembic migrations.

### scenarios
```sql
CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_file_path VARCHAR(500),          -- path in object storage
    source_text TEXT,                        -- extracted plain text
    domain VARCHAR(100) NOT NULL DEFAULT 'general',  -- policy, org_change, crisis, market, fiction
    config JSONB NOT NULL DEFAULT '{}',     -- max_agents, max_ticks, random_seed, etc.
    status VARCHAR(50) NOT NULL DEFAULT 'draft',  -- draft, world_compiled, agents_generated, ready, running, completed
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### world_models
```sql
CREATE TABLE world_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    summary TEXT,                           -- narrative summary of the world
    entities JSONB NOT NULL DEFAULT '[]',   -- [{name, type, description, attributes}]
    factions JSONB NOT NULL DEFAULT '[]',   -- [{name, goals, resources, relationships}]
    resources JSONB NOT NULL DEFAULT '[]',  -- [{name, type, quantity, controlled_by}]
    constraints JSONB NOT NULL DEFAULT '[]', -- [{description, type, severity}]
    tensions JSONB NOT NULL DEFAULT '[]',   -- [{between, description, intensity}]
    kpis JSONB NOT NULL DEFAULT '[]',       -- [{name, description, unit, initial_value, target}]
    raw_extraction JSONB,                   -- full Gemini extraction response for audit
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### agents
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255),
    faction VARCHAR(255),
    personality JSONB NOT NULL DEFAULT '{}',  -- Big Five traits, decision style, risk tolerance
    goals JSONB NOT NULL DEFAULT '[]',        -- [{description, priority, measurable_outcome}]
    resources JSONB NOT NULL DEFAULT '{}',    -- {influence, capital, information, alliances}
    status VARCHAR(50) DEFAULT 'idle',        -- idle, active, eliminated, dormant
    is_chat_enabled BOOLEAN DEFAULT FALSE,
    activation_score FLOAT DEFAULT 0.0,       -- used by selective activation
    working_memory JSONB DEFAULT '{}',        -- current tick context
    episodic_memory JSONB DEFAULT '[]',       -- summarized past events [{tick, summary, emotional_valence}]
    semantic_memory JSONB DEFAULT '{}',       -- compressed long-term knowledge about world
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### simulation_runs
```sql
CREATE TABLE simulation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    random_seed BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, running, paused, completed, failed
    current_tick INTEGER DEFAULT 0,
    max_ticks INTEGER NOT NULL DEFAULT 15,
    config JSONB NOT NULL DEFAULT '{}',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### ticks
```sql
CREATE TABLE ticks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    tick_number INTEGER NOT NULL,
    phase VARCHAR(50) NOT NULL,              -- activation, rules, decisions, state_update, memory_compress, snapshot
    active_agent_ids UUID[] DEFAULT '{}',    -- agents that were LLM-activated this tick
    events JSONB NOT NULL DEFAULT '[]',      -- [{agent_id, action, target, outcome, reasoning}]
    world_state_delta JSONB DEFAULT '{}',    -- changes to world state this tick
    kpi_values JSONB DEFAULT '{}',           -- {kpi_name: current_value}
    snapshot JSONB,                          -- full serialized world state for replay
    interventions_applied UUID[] DEFAULT '{}',
    duration_ms INTEGER,
    gemini_calls INTEGER DEFAULT 0,
    gemini_tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(simulation_run_id, tick_number)
);
```

### interventions
```sql
CREATE TABLE interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,              -- inject_event, modify_agent, modify_world
    payload JSONB NOT NULL,                  -- type-specific intervention data
    description TEXT,
    target_tick INTEGER,                     -- NULL = apply at next tick
    applied_at_tick INTEGER,
    status VARCHAR(50) DEFAULT 'pending',    -- pending, applied, cancelled
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### reports
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    executive_summary TEXT,
    narrative TEXT,                           -- full narrative report
    timeline JSONB NOT NULL DEFAULT '[]',    -- [{tick, title, description, significance}]
    influence_graph JSONB NOT NULL DEFAULT '{}',  -- {nodes: [{id, label, group}], edges: [{source, target, weight, type}]}
    key_findings JSONB DEFAULT '[]',         -- [{finding, evidence, confidence}]
    kpi_trajectories JSONB DEFAULT '{}',     -- {kpi_name: [{tick, value}]}
    counterfactual_notes TEXT,               -- what might have been different
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 3. CORE ENGINE — TICK LOOP (The Heart of the System)

File: `backend/app/engine/orchestrator.py`

The orchestrator runs the main simulation loop. Each tick follows this exact sequence:

```
TICK EXECUTION ORDER:
1. CHECK INTERVENTIONS  → Apply any pending interventions for this tick
2. SELECTIVE ACTIVATION → Score all agents, pick top N for LLM activation
3. RULE RESOLUTION      → Apply deterministic rules BEFORE any LLM calls
4. DECISION ENGINE      → Call Gemini ONLY for activated agents with ambiguous choices
5. STATE UPDATE         → Apply all actions to world state atomically
6. MEMORY COMPRESSION   → Summarize agent memories, prune working memory
7. KPI EVALUATION       → Compute all KPI values for this tick
8. SNAPSHOT             → Serialize full world state for replay
9. EVENT LOG            → Append all events to immutable log
10. BROADCAST           → Push tick summary to WebSocket subscribers
```

### 3.1 Selective Activation (`activation.py`)

This is the key cost-control mechanism. Not every agent calls Gemini every tick.

```python
def compute_activation_scores(agents: list[Agent], world_state: WorldState, tick: int) -> list[tuple[Agent, float]]:
    """
    Score each agent 0.0-1.0 based on:
    - relevance: is this agent's domain affected by recent events?
    - tension: is this agent in a high-conflict situation?
    - goal_proximity: is this agent close to achieving or failing a goal?
    - recency: how recently was this agent last activated?
    - random_jitter: small seeded random factor for variety

    Return sorted list. Top K agents (configurable, default 10-15) get LLM activation.
    The rest execute only deterministic rules or remain idle.
    """
```

### 3.2 Rule Engine (`rule_engine.py`)

Deterministic rules run BEFORE Gemini calls. These are non-negotiable world mechanics:

```python
RULE_TYPES = [
    "resource_decay",        # resources deplete over time
    "alliance_maintenance",  # alliances weaken without interaction
    "threshold_triggers",    # if KPI crosses threshold, trigger event
    "proximity_effects",     # nearby entities influence each other
    "scheduled_events",      # pre-programmed world events at specific ticks
]
```

Rules are extracted from the source document during world compilation and stored in `world_models.constraints`. They execute deterministically with seeded randomness.

### 3.3 Decision Engine (`decision_engine.py`)

For activated agents, use Gemini function calling. Define these callable functions:

```python
AGENT_ACTIONS = [
    "form_alliance",          # {target_agent_id, terms}
    "break_alliance",         # {target_agent_id, reason}
    "publish_statement",      # {content, audience, tone}
    "reallocate_resource",    # {resource_type, amount, from, to}
    "escalate_conflict",      # {target, method, intensity}
    "de_escalate_conflict",   # {target, concession}
    "gather_information",     # {topic, method}
    "influence_agent",        # {target_agent_id, method, goal}
    "change_strategy",        # {new_strategy, reasoning}
    "do_nothing",             # {reasoning} — explicit inaction is an action
]
```

Each action has preconditions (checked by rule engine) and effects (applied by state manager).

### 3.4 Memory Manager (`memory_manager.py`)

Three-layer architecture:

```
WORKING MEMORY (per tick, cleared each tick)
├── Current tick context
├── Immediate perceptions (what happened this tick that affects this agent)
├── Active goals being pursued
└── Recent interactions (last 2 ticks)

EPISODIC MEMORY (rolling window, summarized)
├── List of {tick, event_summary, emotional_valence, importance_score}
├── Max 20 entries per agent
├── When full, compress least-important entries into semantic memory
└── Retrieval: by recency + relevance (embedding similarity)

SEMANTIC MEMORY (compressed long-term, rarely changes)
├── Known facts about other agents
├── Learned world patterns ("when X happens, Y usually follows")
├── Updated alliances and trust scores
└── Generalized strategies that have worked/failed
```

Use Gemini embeddings for retrieval within episodic memory. When an agent is activated, retrieve top 5 most relevant episodic memories to inject into the decision prompt.

---

## 4. GEMINI INTEGRATION

File: `backend/app/gemini/client.py`

Use `google-genai` Python SDK. Configure three distinct usage modes:

### 4.1 Structured Output Mode (Extraction)

Used by `world_compiler.py` and `agent_generator.py`. Define Pydantic models as response schemas:

```python
class WorldExtraction(BaseModel):
    summary: str
    entities: list[EntitySchema]
    factions: list[FactionSchema]
    resources: list[ResourceSchema]
    constraints: list[ConstraintSchema]
    tensions: list[TensionSchema]
    kpis: list[KPISchema]

# Call Gemini with response_mime_type="application/json" and response_schema=WorldExtraction
```

### 4.2 Function Calling Mode (Agent Decisions)

Used by `decision_engine.py`. Register all `AGENT_ACTIONS` as function declarations:

```python
form_alliance_fn = FunctionDeclaration(
    name="form_alliance",
    description="Propose an alliance with another agent",
    parameters={
        "type": "object",
        "properties": {
            "target_agent_id": {"type": "string"},
            "terms": {"type": "string"},
            "offered_resources": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["target_agent_id", "terms"]
    }
)
# Pass all function declarations as tools in the Gemini request
```

### 4.3 Embedding Mode (Memory Retrieval)

Used by `memory_manager.py` for semantic search over episodic memories:

```python
# Use text-embedding-004 model
# Embed: agent episodic memory summaries + current tick context
# Retrieve: top-5 most relevant memories by cosine similarity
```

### Rate Limiting & Cost Control

```python
class GeminiRateLimiter:
    """
    - Track tokens per minute, requests per minute
    - Queue requests when approaching limits
    - Log every call: model, tokens_in, tokens_out, latency_ms, purpose
    - Expose metrics endpoint for monitoring
    - Set hard budget cap per simulation run (configurable)
    """
```

---

## 5. API ENDPOINTS

All endpoints prefixed with `/api/v1/`.

### Scenarios
```
POST   /scenarios                    # Create scenario + upload source file
GET    /scenarios                    # List all scenarios
GET    /scenarios/{id}               # Get scenario details
PUT    /scenarios/{id}               # Update scenario config
DELETE /scenarios/{id}               # Delete scenario and all related data
POST   /scenarios/{id}/compile       # Trigger world model compilation from source
POST   /scenarios/{id}/generate-agents  # Generate agent population from world model
```

### World Model
```
GET    /scenarios/{id}/world         # Get compiled world model
PUT    /scenarios/{id}/world         # Edit world model (user corrections before run)
```

### Simulation
```
POST   /simulations                  # Create + start a simulation run for a scenario
GET    /simulations/{id}             # Get simulation status + current tick
POST   /simulations/{id}/pause      # Pause simulation
POST   /simulations/{id}/resume     # Resume simulation
POST   /simulations/{id}/stop       # Stop simulation early
GET    /simulations/{id}/ticks       # Get all tick data (paginated)
GET    /simulations/{id}/ticks/{n}   # Get specific tick snapshot
GET    /simulations/{id}/replay      # Stream all ticks for replay
```

### Interventions
```
POST   /simulations/{id}/interventions         # Create an intervention
GET    /simulations/{id}/interventions          # List interventions for this run
DELETE /simulations/{id}/interventions/{iid}    # Cancel pending intervention
```

Three intervention types for MVP:
1. **inject_event**: Add an external event to the world ("breaking news", "natural disaster", "policy announcement")
2. **modify_agent**: Change an agent's goals, resources, or status mid-simulation
3. **modify_world**: Change a world resource, constraint, or KPI value

### Agents
```
GET    /simulations/{id}/agents              # List all agents with current state
GET    /simulations/{id}/agents/{aid}        # Get agent detail + memory
POST   /simulations/{id}/agents/{aid}/chat   # Chat with a chat-enabled agent (Gemini-powered, in-character)
```

### Reports
```
POST   /simulations/{id}/report      # Generate final report
GET    /simulations/{id}/report      # Get generated report
```

### WebSocket
```
WS     /ws/simulations/{id}          # Live stream: tick events, KPI updates, agent actions, interventions
```

Message format over WebSocket:
```json
{
  "type": "tick_complete | agent_action | kpi_update | intervention_applied | simulation_complete | error",
  "tick": 5,
  "data": { ... }
}
```

---

## 6. ANGULAR 21 FRONTEND

### Core Patterns

- **All components are standalone** (no NgModules)
- **Use Angular Signals** for reactive state management (no RxJS-heavy stores)
- **Lazy-load** all feature components via the router
- **Use Angular's new control flow** (`@if`, `@for`, `@switch`) instead of `*ngIf`, `*ngFor`
- **Use `inject()` function** instead of constructor injection
- **HttpClient with `provideHttpClient(withFetch())`** for API calls
- **WebSocket service** wraps native WebSocket with auto-reconnect + Signal-based state

### Routes

```typescript
export const routes: Routes = [
  { path: '', redirectTo: '/scenarios', pathMatch: 'full' },
  { path: 'scenarios', loadComponent: () => import('./features/scenario-intake/scenario-intake.component') },
  { path: 'scenarios/:id/world', loadComponent: () => import('./features/world-editor/world-editor.component') },
  { path: 'simulations/:id/control', loadComponent: () => import('./features/simulation-control/simulation-control.component') },
  { path: 'simulations/:id/dashboard', loadComponent: () => import('./features/live-dashboard/live-dashboard.component') },
  { path: 'simulations/:id/intervene', loadComponent: () => import('./features/intervention-console/intervention-console.component') },
  { path: 'simulations/:id/chat', loadComponent: () => import('./features/agent-chat/agent-chat.component') },
  { path: 'simulations/:id/report', loadComponent: () => import('./features/report-viewer/report-viewer.component') },
  { path: 'ensembles/:id', loadComponent: () => import('./features/ensemble-viewer/ensemble-viewer.component') },
  { path: 'auth/login', loadComponent: () => import('./features/auth/login.component') },
  { path: 'auth/register', loadComponent: () => import('./features/auth/register.component') },
];
```

### Screen Specifications

#### 6.1 Scenario Intake
- File upload (drag-and-drop) accepting PDF, DOCX, TXT, MD
- Scenario name, description, domain selector (dropdown: policy, org_change, crisis, market, fiction)
- Configuration panel: max agents (slider 10-100, default 100), max ticks (slider 5-30, default 15), random seed (auto-generate or manual)
- "Compile World" button → calls POST `/scenarios/{id}/compile` → shows progress → navigates to World Editor

#### 6.2 World Editor
- Display extracted world model in editable cards/sections:
  - Summary (editable textarea)
  - Entities (table with inline edit)
  - Factions (cards with goals, relationships visualization)
  - Resources (table)
  - Constraints (list with severity badges)
  - Tensions (list with intensity sliders)
  - KPIs (table with initial values, targets)
- "Regenerate" button per section (re-calls Gemini for that section only)
- "Generate Agents" button → calls POST → shows progress → navigates to Simulation Control

#### 6.3 Simulation Control
- Agent population overview: grid of agent cards showing name, role, faction, status
- Configuration review panel
- Start / Pause / Resume / Stop buttons
- Progress indicator: current tick / max ticks
- Links to Dashboard, Intervention Console, Agent Chat

#### 6.4 Live Dashboard (WebSocket-powered)
- **Tick Timeline**: horizontal scrollable timeline showing completed ticks with key events
- **KPI Gauges**: real-time updating gauges/charts for each KPI using a charting library (use ngx-charts or raw D3)
- **Active Agents Panel**: shows which agents are LLM-activated this tick and their current action
- **Event Feed**: scrolling log of all events this tick
- **World State Summary**: key resource levels, faction power balance (bar chart)
- **Influence Graph**: D3 force-directed graph showing agent-to-agent influence edges (updates each tick)
- All data pushed via WebSocket, rendered via Signals

#### 6.5 Intervention Console
- Three intervention type cards:
  1. **Inject Event**: text area for event description, severity selector, target entities multi-select
  2. **Modify Agent**: agent selector dropdown, editable fields for goals/resources/status
  3. **Modify World**: resource/constraint/KPI selector, new value input
- "Fire at next tick" button
- Intervention history log with status badges (pending, applied, cancelled)

#### 6.6 Agent Chat
- Left sidebar: list of top 10 chat-enabled agents with avatar, name, role, current mood indicator
- Main panel: chat interface with the selected agent
- Agent responds in-character using Gemini, with access to their full memory and current world state
- Show agent's current goals, resources, alliances in a collapsible side panel

#### 6.7 Report Viewer
- **Executive Summary** section
- **Timeline**: vertical timeline visualization of key events across all ticks
- **Influence Graph**: interactive D3 graph showing final influence network
- **KPI Trajectories**: line charts showing each KPI over time with intervention markers
- **Key Findings**: numbered findings with evidence and confidence scores
- **Counterfactual Notes**: what-if analysis section
- Export button: download report as PDF/JSON

### State Management (Signals)

```typescript
// Example: simulation.state.ts
import { signal, computed } from '@angular/core';

export const simulationState = {
  currentRun: signal<SimulationRun | null>(null),
  currentTick: signal<number>(0),
  isRunning: computed(() => simulationState.currentRun()?.status === 'running'),
  ticks: signal<Tick[]>([]),
  kpiValues: signal<Record<string, number[]>>({}),
  activeAgents: signal<Agent[]>([]),
  events: signal<TickEvent[]>([]),
};
```

---

## 7. DOCKER COMPOSE

```yaml
version: '3.8'
services:
  backend:
    build:
      context: ./backend
      dockerfile: ../infra/Dockerfile.backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis
    volumes:
      - uploads:/app/uploads

  frontend:
    build:
      context: ./frontend
      dockerfile: ../infra/Dockerfile.frontend
    ports:
      - "4200:80"
    depends_on:
      - backend

  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: swarmscope
      POSTGRES_USER: swarmscope
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
  uploads:
```

---

## 8. ENVIRONMENT VARIABLES (.env.example)

```env
# Gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-pro
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_MAX_TOKENS_PER_MINUTE=1000000
GEMINI_MAX_REQUESTS_PER_MINUTE=60
GEMINI_BUDGET_PER_RUN_USD=5.00
GEMINI_BUDGET_PER_ENSEMBLE_USD=25.00

# External Data Ingestion
NEWS_API_KEY=optional-newsapi-key
WEBHOOK_RATE_LIMIT_PER_MINUTE=5
MAX_INGESTED_EVENTS_PER_TICK=20

# Database
DATABASE_URL=postgresql+asyncpg://swarmscope:password@postgres:5432/swarmscope
POSTGRES_PASSWORD=change-me-in-production

# Redis
REDIS_URL=redis://redis:6379/0

# App
APP_ENV=development
APP_SECRET_KEY=change-me
CORS_ORIGINS=http://localhost:4200
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=/app/uploads
```

---

## 9. BUILD ORDER

Execute in this sequence:

### Phase 1: Foundation
1. Initialize the monorepo structure
2. Set up `pyproject.toml` with dependencies: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `google-genai`, `redis`, `python-multipart`, `pypdf`, `python-docx`, `python-jose[cryptography]`, `passlib[bcrypt]`, `numpy`, `httpx`
3. Set up Angular 21 project: `ng new frontend --standalone --style=scss --routing`
4. Create `docker-compose.yml` and Dockerfiles
5. Create Alembic config and initial migration with all tables
6. Create `.env.example`

### Phase 2: Backend Core
7. Implement `config.py` with Pydantic Settings
8. Implement all SQLAlchemy models
9. Implement all Pydantic schemas
10. Implement `dependencies.py` (DB session, Redis, Gemini client)
11. Implement `main.py` (FastAPI app with CORS, lifespan, router mount)
12. Implement file parser utility (PDF, DOCX, TXT, MD → plain text)

### Phase 3: Gemini Layer
13. Implement Gemini client wrapper with rate limiting
14. Implement all prompt templates
15. Implement extraction module (structured output)
16. Implement decision module (function calling)
17. Implement embedding module

### Phase 4: Engine
18. Implement world compiler (source text → WorldModel via Gemini extraction)
19. Implement agent generator (WorldModel → Agent population via Gemini)
20. Implement activation scoring
21. Implement rule engine
22. Implement decision engine
23. Implement state manager
24. Implement memory manager (3-layer with compression)
25. Implement event log
26. Implement intervention handler
27. Implement orchestrator (tick loop wiring everything together)

### Phase 5: API
28. Implement all REST endpoints
29. Implement WebSocket endpoint for live streaming
30. Implement simulation worker (background tick execution)
31. Implement report worker (post-run analysis)

### Phase 6: Frontend
32. Create all services (API, WebSocket, scenario, simulation, intervention, report)
33. Create shared components (file-upload, agent-card, tick-timeline, kpi-gauge, influence-graph)
34. Build Scenario Intake screen
35. Build World Editor screen
36. Build Simulation Control screen
37. Build Live Dashboard screen (WebSocket integration)
38. Build Intervention Console screen
39. Build Agent Chat screen
40. Build Report Viewer screen

### Phase 7: Authentication & Security
41. Implement User model, JWT auth, register/login/refresh endpoints
42. Add `get_current_user` dependency, scope all queries to current user
43. Build login/register Angular components + auth interceptor

### Phase 8: Knowledge Graph & Influence Tracking
44. Implement knowledge graph endpoint (D3-compatible nodes+edges from world model)
45. Build knowledge-graph-viewer Angular component (D3 force-directed)
46. Integrate into World Editor (editable) and Live Dashboard (read-only)
47. Implement influence_tracker.py (edge creation per agent action)
48. Build influence graph endpoints and integrate into dashboard + report

### Phase 9: Enhanced Reporting & Surveys
49. Upgrade report_worker to use Gemini function calling with 5 report tools
50. Add tool usage log to report output and Report Viewer UI
51. Implement survey_executor.py + survey endpoints
52. Build survey UI component in Agent Chat screen

### Phase 10: Forking & Scenario Library
53. Implement fork_manager.py (restore from tick snapshot, create new run)
54. Add fork endpoint + "Fork" button in Tick Timeline component
55. Build scenario-library component (card grid, clone, filter, search)

### Phase 11: Ensemble Mode
56. Implement ensemble_runs table + migration
57. Implement ensemble_runner.py (parallel multi-seed execution with asyncio.gather)
58. Implement ensemble_aggregator.py (KPI stats, influence stability, robustness score — requires numpy)
59. Implement ensemble API endpoints (create, status, statistics, per-KPI detail)
60. Build ensemble-viewer Angular component (robustness gauge, KPI confidence bands, influence heatmap, run comparison table)
61. Add "Run Ensemble" button + cost estimate modal to Simulation Control screen

### Phase 12: Live External Data Ingestion
62. Implement ingestion_sources and ingested_events tables + migration
63. Implement ingestion_handler.py (webhook processing, Gemini summarization, mapping rules)
64. Implement ingestion_worker.py (scheduled pull background worker)
65. Implement webhook receiver endpoint with HMAC verification
66. Implement ingestion source CRUD API endpoints
67. Update orchestrator.py tick loop: add step 0 (check external sources)
68. Build ingestion source config UI in Scenario Intake screen
69. Build "External Events Feed" panel in Live Dashboard
70. Add external_event_ingested WebSocket message type

### Phase 13: Integration & Polish
71. End-to-end test: register → upload document → compile world → edit world → generate agents → run simulation → intervene → fork → survey → ensemble → ingest external data → generate report
72. Add error handling, loading states, and toast notifications throughout
73. Add cost tracking dashboard (Gemini tokens used per run and per ensemble)
74. Write README with setup instructions

---

## 10. NEW FEATURES (Post-MiroFish Analysis Additions)

These features were identified after deep analysis of MiroFish's codebase and represent critical differentiators.

### 10.1 Authentication (JWT)

Add basic JWT auth from day one. MiroFish has zero auth (GitHub Issue #487).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

Add `user_id UUID REFERENCES users(id)` to the `scenarios` table.

New files:
- `backend/app/api/auth.py` — register, login, refresh endpoints
- `backend/app/models/user.py` — User SQLAlchemy model
- `backend/app/schemas/auth.py` — LoginRequest, TokenResponse
- `backend/app/dependencies.py` — add `get_current_user` dependency using `python-jose` for JWT

Endpoints:
```
POST /auth/register     # {email, password} → {user_id, token}
POST /auth/login        # {email, password} → {access_token, refresh_token}
POST /auth/refresh      # {refresh_token} → {access_token}
```

All other endpoints require `Authorization: Bearer <token>` header. Scope all queries to current user.

Frontend: Add `auth/login.component.ts` and `auth/register.component.ts`. Store token in memory (not localStorage). Add `auth.interceptor.ts` to attach token to all API requests.

### 10.2 Knowledge Graph Visualization

MiroFish's GraphPanel (D3 force-directed graph) is one of its strongest UI features. SwarmScope needs this.

New shared component: `frontend/src/app/shared/components/knowledge-graph-viewer/`

Use D3.js force simulation within Angular:
- Nodes = entities (circles) + factions (hexagons)
- Edges = relationships + tensions (colored by intensity)
- Node size = influence/resource level
- Edge thickness = relationship strength
- Clickable nodes open edit panel in World Editor
- During simulation: graph updates live as relationships change via WebSocket

New API endpoint:
```
GET /scenarios/{id}/knowledge-graph    # Returns D3-compatible {nodes: [...], edges: [...]}
```

Display in:
- **World Editor** — full interactive graph with edit-on-click
- **Live Dashboard** — read-only graph updating per tick
- **Report Viewer** — final state influence graph

### 10.3 Tool-Augmented Report Generation

MiroFish's ReACT report agent with 4 tools is well-designed. Match and exceed it.

Update `backend/app/workers/report_worker.py` to use Gemini function calling with these tools:

```python
REPORT_TOOLS = [
    "query_tick_data",        # Retrieve events from specific ticks with filters
    "analyze_kpi_trajectory", # Compute trend, inflection points, correlation for a KPI
    "compare_agent_outcomes", # Cross-agent comparison: who gained/lost the most
    "interview_agent",        # Post-sim Gemini call: ask an agent a question in-character
    "find_causal_chain",      # Trace cause→effect chain through tick events
]
```

Report generation flow:
1. **Planning call**: Gemini receives simulation summary → outputs report outline (sections + which tools to use per section)
2. **Per-section generation**: Gemini writes each section, calling tools as needed (max 5 tool calls per section)
3. **Reflection**: After all sections, Gemini reviews for consistency (max 2 reflection rounds)

Show tool usage log in Report Viewer UI (which tool was called, what it returned, how it informed the narrative).

### 10.4 Influence Tracking

MiroFish has no agent-to-agent influence concept. This powers our influence graph.

New database table:
```sql
CREATE TABLE influence_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    source_agent_id UUID NOT NULL REFERENCES agents(id),
    target_agent_id UUID NOT NULL REFERENCES agents(id),
    action_type VARCHAR(100) NOT NULL,
    tick_number INTEGER NOT NULL,
    weight FLOAT NOT NULL DEFAULT 1.0,
    context TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

New engine file: `backend/app/engine/influence_tracker.py`

Every agent action that targets another agent creates an influence edge:
- `form_alliance` → weight 2.0
- `influence_agent` → weight 1.5
- `publish_statement` → weight 0.5 (targets audience, not specific agent)
- `escalate_conflict` → weight -2.0 (negative influence)

New endpoints:
```
GET /simulations/{id}/influence-graph              # Full graph {nodes, edges} with accumulated weights
GET /simulations/{id}/influence-graph/agent/{aid}   # Ego network for one agent
```

### 10.5 Scenario Library Page

MiroFish has a history dashboard. SwarmScope needs one too.

New feature component: `frontend/src/app/features/scenario-library/scenario-library.component.ts`

This replaces the simple scenarios list. Shows:
- Card grid of all user's scenarios
- Status badges per stage: draft → world_compiled → agents_generated → running → completed → report_generated
- Last run date, tick count, agent count, domain tag
- Search by name, filter by domain and status
- "Clone Scenario" action → duplicates scenario config + world model for running variations
- "Delete" with confirmation

Route: `/scenarios` (same as before, but richer component)

### 10.6 Survey / Batch Agent Interview

New engine file: `backend/app/engine/survey_executor.py`

```sql
CREATE TABLE surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    target_agent_ids UUID[] NOT NULL,
    response_format VARCHAR(50) DEFAULT 'free_text',
    responses JSONB DEFAULT '[]',
    aggregate_analysis JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

New endpoints:
```
POST /simulations/{id}/survey     # {question, target_agent_ids, response_format}
GET  /simulations/{id}/surveys    # List all surveys for this simulation
GET  /simulations/{id}/surveys/{sid}  # Get survey results
```

Flow:
1. User submits question + selects target agents (or "all chat-enabled")
2. Backend makes parallel Gemini calls: each agent responds in-character
3. Backend runs aggregate analysis: sentiment distribution, keyword extraction, consensus score
4. Results displayed in Agent Chat screen as a survey results card

### 10.7 Simulation Forking (Fork from Tick)

MiroFish has no rollback or branching. This is a killer feature.

Add to `simulation_runs` table:
```sql
ALTER TABLE simulation_runs ADD COLUMN forked_from_tick_id UUID REFERENCES ticks(id);
```

New engine file: `backend/app/engine/fork_manager.py`

New endpoint:
```
POST /simulations/{id}/fork-from-tick/{tick_id}    # {new_config, interventions_to_apply}
```

Flow:
1. Load the snapshot from the specified tick
2. Create a new `simulation_run` with `forked_from_tick_id` set
3. Restore world state, agent states, memory from snapshot
4. Apply any new interventions the user specified
5. Resume tick execution from that point

UI: In the Tick Timeline component, each tick has a "Fork" button. Clicking it opens a modal to optionally add interventions, then starts a new run.

### 10.8 Ensemble Mode (Multi-Run Statistics)

This is the single most important feature for enterprise credibility. A single simulation run is an anecdote. Multiple runs with statistical aggregation is evidence.

**What it does:** Run the same scenario N times (default 5, max 10) with different random seeds. Aggregate results to show mean, variance, and confidence intervals on all KPIs and influence relationships.

#### Database Changes

```sql
-- Parent table for ensemble runs
CREATE TABLE ensemble_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    ensemble_size INTEGER NOT NULL DEFAULT 5 CHECK (ensemble_size BETWEEN 2 AND 10),
    base_config JSONB NOT NULL DEFAULT '{}',       -- shared config for all child runs
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    statistics JSONB,                               -- computed after all runs complete
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Link simulation_runs to their parent ensemble
ALTER TABLE simulation_runs ADD COLUMN ensemble_run_id UUID REFERENCES ensemble_runs(id);
ALTER TABLE simulation_runs ADD COLUMN ensemble_seed_index INTEGER;  -- 0, 1, 2, ... N-1
```

The `statistics` JSONB stores the computed aggregation:
```json
{
  "kpi_statistics": {
    "public_approval": {
      "per_tick": [
        {"tick": 1, "mean": 62.3, "std": 4.1, "min": 55.0, "max": 68.0, "ci_95_low": 58.2, "ci_95_high": 66.4},
        {"tick": 2, "mean": 59.1, "std": 5.8, "min": 50.0, "max": 67.0, "ci_95_low": 53.3, "ci_95_high": 64.9}
      ],
      "final": {"mean": 45.2, "std": 8.3, "ci_95_low": 36.9, "ci_95_high": 53.5}
    }
  },
  "influence_statistics": {
    "stable_relationships": [{"source": "agent_a", "target": "agent_b", "mean_weight": 3.2, "variance": 0.1}],
    "volatile_relationships": [{"source": "agent_c", "target": "agent_d", "mean_weight": 1.1, "variance": 2.8}]
  },
  "outcome_consistency": {
    "robustness_score": 0.73,         -- 0-1, how consistent outcomes are across runs
    "divergence_tick": 7,             -- tick where runs start diverging significantly
    "most_variable_kpi": "market_share",
    "most_stable_kpi": "regulatory_compliance"
  },
  "run_summaries": [
    {"run_index": 0, "seed": 12345, "final_kpis": {...}, "key_event": "Alliance formed at tick 3"},
    {"run_index": 1, "seed": 67890, "final_kpis": {...}, "key_event": "Conflict escalated at tick 5"}
  ]
}
```

#### New Engine Files

**`backend/app/engine/ensemble_runner.py`**

```python
class EnsembleRunner:
    """
    Orchestrates N parallel simulation runs with different seeds.
    
    Flow:
    1. Create ensemble_run record
    2. Generate N random seeds (deterministically from a base seed for reproducibility)
    3. For each seed: create a simulation_run linked to the ensemble
    4. Execute all runs (concurrently via asyncio.gather with semaphore limiting to 3 parallel runs)
    5. After all complete: compute statistics
    6. Store aggregated results in ensemble_runs.statistics
    """
    
    async def run_ensemble(self, scenario_id: UUID, ensemble_size: int, base_config: dict) -> EnsembleRun:
        pass
    
    def _generate_seeds(self, base_seed: int, count: int) -> list[int]:
        """Deterministic seed generation: Random(base_seed).randint() × count"""
        pass
```

**`backend/app/engine/ensemble_aggregator.py`**

```python
class EnsembleAggregator:
    """
    Computes statistics across N completed simulation runs.
    
    Methods:
    - aggregate_kpis(): For each KPI, compute per-tick mean/std/min/max/CI across runs
    - aggregate_influence(): Classify relationships as stable (low variance) vs volatile (high variance)
    - compute_robustness_score(): Overall consistency metric (inverse of normalized KPI variance)
    - find_divergence_point(): First tick where inter-run KPI variance exceeds threshold
    - generate_run_summaries(): One-line summary per run highlighting its distinguishing event
    
    Uses numpy for statistical computation (add to dependencies).
    """
    
    def aggregate(self, simulation_run_ids: list[UUID]) -> dict:
        pass
```

#### API Endpoints

```
POST   /ensembles                          # {scenario_id, ensemble_size, base_config} → starts ensemble
GET    /ensembles/{id}                     # Get ensemble status + statistics
GET    /ensembles/{id}/runs                # List all simulation runs in this ensemble
GET    /ensembles/{id}/statistics           # Get aggregated statistics only
GET    /ensembles/{id}/kpi/{kpi_name}      # Per-KPI detail: all runs + aggregate curve
DELETE /ensembles/{id}                     # Cancel running ensemble or delete completed
```

#### Frontend: Ensemble Statistics Screen

New feature component: `frontend/src/app/features/ensemble-viewer/ensemble-viewer.component.ts`

Route: `/ensembles/{id}`

**Screen sections:**

1. **Robustness Summary Card**
   - Robustness score as a large gauge (0-100%)
   - Divergence tick indicator
   - Most stable / most variable KPI badges
   - Ensemble size and total runs completed

2. **KPI Trajectory Chart (with confidence bands)**
   - X-axis: ticks, Y-axis: KPI value
   - Bold line: mean trajectory across all runs
   - Shaded band: 95% confidence interval
   - Thin lines (toggleable): individual run trajectories
   - One chart per KPI, switchable via tabs
   - Use D3 or ngx-charts with area fills for confidence bands

3. **Influence Stability Matrix**
   - Heatmap of agent-to-agent influence
   - Color: green = stable (low variance), red = volatile (high variance)
   - Hover shows: mean weight ± std across runs

4. **Run Comparison Table**
   - One row per run: seed, final KPI values, key distinguishing event
   - Click row → navigates to that run's full dashboard
   - Sortable by any KPI column

5. **Cost Summary**
   - Total Gemini calls across all runs
   - Total tokens used
   - Estimated cost

**Entry point:** Add "Run Ensemble" button next to "Start Simulation" in Simulation Control screen. Opens a modal to configure ensemble_size (slider 2-10) and shows estimated cost (ensemble_size × single_run_cost).

#### Cost Control

- Show estimated cost before starting: `ensemble_size × estimated_single_run_cost`
- User must confirm before launching (modal with cost estimate)
- Each child run respects the existing `GEMINI_BUDGET_PER_RUN_USD` cap
- Add `GEMINI_BUDGET_PER_ENSEMBLE_USD` env var (default: ensemble_size × single_run_budget)
- If any run exceeds budget, it stops but other runs continue
- Partial ensembles (e.g., 4 of 5 completed) still compute statistics with a warning

#### Dependencies

Add `numpy` to `pyproject.toml` for statistical computations (mean, std, percentile, confidence intervals).

---

### 10.9 Live External Data Ingestion

Allow real-world data to feed into running simulations as automatic interventions. Turns static "what-if" scenarios into living forecasters.

#### Database Changes

```sql
-- Ingestion source configuration
CREATE TABLE ingestion_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,                     -- "Reuters News Feed", "Stock API", etc.
    source_type VARCHAR(50) NOT NULL,               -- 'webhook' or 'scheduled_pull'
    config JSONB NOT NULL DEFAULT '{}',             -- type-specific config
    webhook_secret VARCHAR(255),                    -- HMAC secret for webhook verification
    mapping_rules JSONB NOT NULL DEFAULT '{}',      -- how to convert raw events → interventions
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Log of all ingested events
CREATE TABLE ingested_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingestion_source_id UUID NOT NULL REFERENCES ingestion_sources(id) ON DELETE CASCADE,
    simulation_run_id UUID REFERENCES simulation_runs(id),
    raw_payload JSONB NOT NULL,                     -- original data received
    processed_intervention JSONB,                   -- the intervention it was converted to
    intervention_id UUID REFERENCES interventions(id),  -- link to created intervention
    status VARCHAR(50) DEFAULT 'received',          -- received, processing, converted, applied, rejected, error
    rejection_reason TEXT,                           -- why it was rejected (if filtered out)
    received_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);
```

#### Ingestion Source Config Examples

**Webhook mode** (`source_type: 'webhook'`):
```json
{
  "config": {
    "description": "Receives events from external systems via HTTP POST"
  },
  "mapping_rules": {
    "event_field": "headline",           -- which field in payload contains the event description
    "severity_field": "importance",       -- optional: map to intervention severity
    "entity_field": "entities",           -- optional: map to affected entities
    "default_intervention_type": "inject_event",
    "gemini_summarize": true             -- use Gemini to convert raw data into a simulation-meaningful event
  }
}
```

**Scheduled pull mode** (`source_type: 'scheduled_pull'`):
```json
{
  "config": {
    "url": "https://newsapi.org/v2/everything",
    "method": "GET",
    "headers": {"X-Api-Key": "{{NEWS_API_KEY}}"},
    "params": {"q": "{{scenario_keywords}}", "sortBy": "publishedAt", "pageSize": 5},
    "poll_interval_ticks": 3             -- fetch every 3 ticks
  },
  "mapping_rules": {
    "response_path": "articles",          -- JSONPath to array of events in response
    "event_field": "title",
    "detail_field": "description",
    "gemini_summarize": true
  }
}
```

#### New Engine Files

**`backend/app/engine/ingestion_handler.py`**

```python
class IngestionHandler:
    """
    Processes incoming external data and converts to interventions.
    
    Flow:
    1. Receive raw event (from webhook endpoint or scheduled pull)
    2. Validate against rate limits
    3. Apply mapping rules to extract event description
    4. If gemini_summarize=True: call Gemini to convert raw data into
       a simulation-meaningful event description with affected entities
    5. Create an intervention record (type=inject_event, target_tick=next)
    6. Log to ingested_events table
    7. Push notification to WebSocket subscribers
    
    Gemini prompt for summarization:
    "Given this external data event and the current simulation world model,
     describe how this event would affect the simulated scenario.
     Output: {event_description, severity, affected_entities[], suggested_impact}"
    """
    
    async def process_webhook_event(self, source_id: UUID, payload: dict) -> IngestedEvent:
        pass
    
    async def run_scheduled_pull(self, source_id: UUID, simulation_run_id: UUID) -> list[IngestedEvent]:
        pass
    
    def _apply_mapping_rules(self, payload: dict, rules: dict) -> dict:
        pass
    
    async def _gemini_summarize(self, raw_text: str, world_model_summary: str) -> dict:
        pass
```

**`backend/app/workers/ingestion_worker.py`**

```python
class IngestionWorker:
    """
    Background worker for scheduled pull sources.
    
    Runs alongside simulation_worker. Each tick, checks if any scheduled_pull
    sources are due (based on poll_interval_ticks). If so, fetches data,
    processes through IngestionHandler, and queues interventions for next tick.
    
    Integrates with orchestrator: orchestrator calls ingestion_worker.check_sources()
    at the start of each tick, before intervention processing.
    """
```

#### API Endpoints

```
# Ingestion source management
POST   /scenarios/{id}/ingestion-sources           # Create ingestion source
GET    /scenarios/{id}/ingestion-sources            # List sources for scenario
PUT    /scenarios/{id}/ingestion-sources/{sid}      # Update source config
DELETE /scenarios/{id}/ingestion-sources/{sid}      # Remove source
POST   /scenarios/{id}/ingestion-sources/{sid}/test # Test source with mock data

# Webhook receiver (no auth — uses webhook_secret for HMAC verification)
POST   /webhooks/ingest/{source_id}                # External systems POST here
                                                    # Header: X-Webhook-Signature for HMAC

# Ingestion logs
GET    /simulations/{id}/ingested-events           # List all ingested events for a run
GET    /simulations/{id}/ingested-events/{eid}     # Get single event detail + linked intervention
```

#### Orchestrator Integration

Update `backend/app/engine/orchestrator.py` tick loop — add step 0 before intervention checking:

```
UPDATED TICK EXECUTION ORDER:
0. CHECK EXTERNAL SOURCES → Run ingestion_worker.check_sources() for scheduled pulls
1. CHECK INTERVENTIONS    → Apply pending interventions (including auto-created from ingestion)
2. SELECTIVE ACTIVATION   → Score all agents, pick top N for LLM activation
... (rest unchanged)
```

#### Frontend Changes

**Scenario Intake screen additions:**
- "External Data Sources" collapsible section below the configuration panel
- "Add Source" button → modal with:
  - Name input
  - Type selector: Webhook / Scheduled Pull
  - For Webhook: shows generated webhook URL + secret (copy-to-clipboard)
  - For Scheduled Pull: URL, headers, params, poll interval
  - Mapping rules: event field, severity field, Gemini summarize toggle
  - "Test Connection" button

**Live Dashboard additions:**
- New "External Events Feed" panel (toggleable)
- Shows incoming events as they arrive: timestamp, source name, raw summary, status badge
- Events that became interventions show a link to the intervention in the Intervention Console
- Events that were rejected show the reason

**WebSocket message type addition:**
```json
{
  "type": "external_event_ingested",
  "tick": 5,
  "data": {
    "source_name": "Reuters News Feed",
    "event_summary": "Major trade agreement announced between...",
    "intervention_created": true,
    "intervention_id": "uuid"
  }
}
```

#### Security & Rate Limiting

- Webhook endpoints use HMAC-SHA256 verification: `X-Webhook-Signature` header must match `HMAC(webhook_secret, request_body)`
- Per-source rate limit: configurable, default 5 events/minute
- Global rate limit: max 20 ingested events per tick across all sources
- Events exceeding rate limits are logged with status `rejected` and reason `rate_limited`
- Gemini summarization calls count toward the per-run budget cap
- User can pause/resume individual sources without deleting them (`is_active` toggle)

---

## 11. KEY IMPLEMENTATION NOTES

1. **Determinism**: Every random operation must use `random.Random(seed)` — never use global random state. The same seed + same document + same config must produce the same simulation, barring Gemini stochasticity (which should be logged).

2. **Event Sourcing**: The `ticks` table IS the event log. Every tick stores a full snapshot. Any simulation can be replayed from tick 0 by loading snapshots sequentially. Never mutate past tick records.

3. **Selective Activation Budget**: Default to activating max 15 agents per tick out of 100. This keeps Gemini costs at roughly 15 calls per tick × 15 ticks = 225 Gemini calls per simulation run — manageable and debuggable.

4. **Memory Compression**: After each tick, if an agent's episodic memory exceeds 20 entries, use Gemini to summarize the 5 least-important entries into 1 semantic memory update. This keeps context windows small.

5. **WebSocket Protocol**: Use a single WebSocket connection per simulation viewer. Server sends JSON messages typed by event. Client reconnects automatically on disconnect.

6. **Agent Chat**: When a user chats with an agent, construct a Gemini prompt that includes: agent profile, current goals, semantic memory, last 5 episodic memories, current world state summary, and the user's message. The agent responds in character. This is a separate Gemini call outside the tick loop.

7. **Report Generation**: After simulation completes, the report worker makes a single large Gemini call with: world model summary, all tick events (summarized), KPI trajectories, and intervention log. It produces a structured report with executive summary, timeline, findings, and counterfactual analysis.

8. **File Upload**: Accept files up to 50MB. Parse PDFs with `pypdf`, DOCX with `python-docx`, TXT/MD as plain text. Store original in uploads directory, extracted text in `scenarios.source_text`.

9. **Error Handling**: Every Gemini call must be wrapped in retry logic (3 retries with exponential backoff). If Gemini fails after retries for an agent decision, log the failure and have the agent execute `do_nothing` for that tick.

10. **CORS**: Configure for `http://localhost:4200` in development. The frontend proxies API calls through Angular's proxy config in development.

---

## PROMPT END
