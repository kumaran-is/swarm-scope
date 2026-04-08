# MiroFish Deep Analysis & SwarmScope Differentiation Plan

> Based on reading actual MiroFish source code with file:line citations. Zero speculation.

---

## PART 1: WHAT MIROFISH ACTUALLY IS (Evidence-Based)

### 1.1 Architecture Reality

MiroFish is **NOT a standalone simulation engine**. It is an **orchestration wrapper** around the [OASIS framework](https://github.com/camel-ai/oasis) (AGPL-3.0 licensed). MiroFish manages configuration, profiles, and persistence; OASIS handles the actual agent execution.

**Evidence:**
- `backend/scripts/run_reddit_simulation.py:577-582` — creates OASIS environment: `self.env = oasis.make(platform=oasis.DefaultPlatformType.REDDIT, database_path=db_path, semaphore=30)`
- `backend/requirements.txt` — depends on `camel-ai[all]` and `oasis` packages
- Agent decisions are delegated entirely to OASIS via `LLMAction()` objects (line 638-643)

**What this means for SwarmScope:** We own our engine. No OASIS dependency, no AGPL license risk, no black-box agent decisions. This is a fundamental architectural advantage.

### 1.2 Simulation Loop (Tick-Based, But Limited)

MiroFish runs a tick-based loop with 60-minute simulated increments per round.

**Evidence** (`run_reddit_simulation.py:626-651`):
```
FOR round_num in range(total_rounds):
  → compute simulated_hour from round_num
  → _get_active_agents_for_round() — stochastic filtering by time-of-day + activity_level
  → build action dict: {agent: LLMAction() for active agents}
  → await self.env.step(actions) — BLOCKING, all agents act in parallel (semaphore=30)
  → log progress every 10 rounds
```

**Gaps identified:**
- No deterministic rule resolution before LLM calls — everything goes to LLM
- No event sourcing — state saved as snapshots only (`simulation_manager.py:145-155`)
- No pause/resume — simulation must complete or be killed
- No random seed set (`run_reddit_simulation.py:21-24` — no `random.seed()` call found)
- Runs are **non-reproducible**

### 1.3 Selective Activation (Exists, But Stochastic Only)

MiroFish does activate agents selectively per round, which was our planned differentiator. However, their approach is purely **time-of-day + random probability**, not relevance-based.

**Evidence** (`run_reddit_simulation.py:469-521`):
- Agents filtered by `active_hours` (time-of-day gate)
- Then `random.random() < activity_level` (random probability)
- Peak hour multiplier: 1.5x (19-22h), off-peak: 0.3x (0-5h)
- Target count: `random.uniform(base_min, base_max) * multiplier`

**What this means for SwarmScope:** Their activation is scheduling-based ("who's online at this hour"). Ours should be **relevance-based** ("who is most affected by what just happened"). This is a genuine differentiator worth keeping.

### 1.4 Agent Memory & Context

MiroFish uses **Zep Cloud** as an external graph memory service. Agents don't have internal multi-layer memory.

**Evidence:**
- `backend/app/services/zep_graph_memory_updater.py:24-62` — activities encoded as natural language episodes and posted to Zep
- `backend/app/services/zep_entity_reader.py` — entity context retrieved via `client.graph.node.get()` + `get_entity_edges()`
- Episode format: `"在{platform}发布了帖子：「{content}」"` (Chinese language templates)

**Gaps:**
- No working/episodic/semantic memory layers — just raw episode feed into Zep
- Memory is append-only, no compression or summarization
- Zep free tier causes rate limiting failures (Issue #60: "429 限流导致图谱构建失败")
- No memory retrieval during agent decisions — only during report generation

**What this means for SwarmScope:** Our 3-layer memory design (working/episodic/semantic) with Gemini embeddings for retrieval is a significant upgrade. Agents will actually use memory during decisions, not just store it.

### 1.5 LLM Integration

MiroFish uses OpenAI SDK format (defaulting to Alibaba Qwen-plus), with structured JSON output via `response_format={"type": "json_object"}`.

**Evidence:**
- `backend/app/config.py:22-33` — `LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')`
- `backend/app/utils/llm_client.py` — two methods: `chat()` and `chat_json()`
- JSON repair pipeline: strips `<think>` tags, markdown fences, then `json.loads()`
- Default temperature: 0.7 (chat), 0.3 (JSON)
- Max tokens: 4096 per call

**Cost per simulation:**
| Phase | LLM Calls | Estimated Cost |
|-------|-----------|---------------|
| Ontology generation | 1 | $0.001 |
| Profile generation (100 agents) | ~100 | $0.020 |
| Config generation | ~15 | $0.015 |
| OASIS simulation (per agent per round) | all active agents × all rounds | **unbounded** |
| Report generation | ~15-20 | $0.050 |

**Critical gap:** No per-simulation budget cap, no rate limiting, no cost tracking. `.env.example` only warns: "try fewer than 40 rounds first."

**What this means for SwarmScope:** Our Gemini rate limiter with per-run budget caps (`GEMINI_BUDGET_PER_RUN_USD=5.00`) and selective activation (max 15 agents/tick) makes cost predictable. This is a major enterprise selling point.

### 1.6 World Model

MiroFish uses Zep's knowledge graph as the world model, built from uploaded documents via an ontology generation pipeline.

**Evidence** (`backend/app/services/ontology_generator.py`):
- Extracts `entity_types[]` and `edge_types[]` from source documents
- Max 10 entity types, max 10 edge types (hardcoded limits)
- Text truncated to 50,000 chars
- Output: PascalCase entities, UPPER_SNAKE_CASE relationships

**Evidence** (`backend/app/services/graph_builder.py`):
- Creates Zep graph with dynamic Pydantic models
- Adds document text in batches as episodes
- Polls `episode.processed` status (retries every 3s, timeout 600s)

**Gaps:**
- No explicit factions, resources, constraints, tensions, or KPIs extracted
- No world rules or deterministic mechanics
- The "world" is a knowledge graph, not a simulation state machine
- Users **cannot edit** the extracted world model (no edit UI found in any frontend component)

**What this means for SwarmScope:** Our WorldModel with explicit entities, factions, goals, resources, constraints, tensions, and measurable KPIs is far richer. The editable World Editor screen lets users correct extraction errors before running. MiroFish's users are stuck with whatever the LLM extracted.

### 1.7 Intervention System (God's Eye View)

MiroFish has limited post-simulation interventions, not mid-simulation interventions.

**Evidence** (`run_reddit_simulation.py:214-298`):
- Interviews via IPC: writes JSON command files to `ipc_commands/`, reads responses from `ipc_responses/`
- Only `INTERVIEW` action type — asks an agent a question and gets a response
- Executed AFTER simulation completes, not during
- No event injection, no world modification, no agent modification mid-run

**Frontend evidence:** No intervention UI found in any Vue component (confirmed by frontend analysis). Step 5 has agent chat but no God's-eye intervention console.

**What this means for SwarmScope:** Our 3 intervention types (inject_event, modify_agent, modify_world) during active simulation are completely absent from MiroFish. This is a headline differentiator.

### 1.8 Platform Hardcoding

MiroFish is deeply tied to Twitter and Reddit simulation.

**Evidence:**
- `backend/app/config.py` — fixed action enums per platform:
  - Twitter: `CREATE_POST, LIKE_POST, REPOST, FOLLOW, DO_NOTHING, QUOTE_POST`
  - Reddit: `LIKE_POST, DISLIKE_POST, CREATE_POST, CREATE_COMMENT, ...`
- `run_parallel_simulation.py:177-200` — separate runner scripts per platform
- Separate profile formats: JSON for Reddit, CSV for Twitter
- Adding TikTok/Douyin (Issue #476) required forking OASIS and adding ~740 lines across 9 files

**What this means for SwarmScope:** Our domain-agnostic action system (`form_alliance`, `publish_statement`, `reallocate_resource`, `escalate_conflict`, etc.) works across any scenario type. No platform-specific code paths.

### 1.9 Report Generation

MiroFish has a sophisticated ReACT-pattern report agent with 4 tools.

**Evidence** (`backend/app/services/report_agent.py`):
- Two-phase: planning (outline) → execution (section-by-section)
- 4 tools: `InsightForge` (deep retrieval), `PanoramaSearch` (breadth-first), `QuickSearch` (lightweight), `InterviewAgents` (batch agent interviews)
- Max 5 tool calls per section, max 2 reflection rounds
- Temperature: 0.5

**This is well done.** Our report generation should match or exceed this quality.

### 1.10 Security & Production Readiness

MiroFish has **4 critical unresolved security vulnerabilities**:

**Evidence (GitHub Issues):**
- **#483** — Werkzeug RCE (CVSS 10.0): Flask debug mode enabled by default
- **#487** — No authentication on any endpoint (CVSS 9.1): 50+ REST endpoints with zero auth
- **#488** — Cross-tenant command injection (CVSS 8.2): unvalidated simulation_id in IPC
- **#489** — SQLite path traversal (CVSS 7.5): platform parameter directly interpolated into DB path

**Issue #421** — Maintainer formally documented 4 blockers before production:
1. Async execution layer needed (IPC polling causes race conditions)
2. Authentication & input validation needed
3. AGPL compliance with OASIS dependency
4. Agent quality improvements needed

**What this means for SwarmScope:** We're building production-grade from day one — FastAPI with proper dependency injection, PostgreSQL (not SQLite), authentication-ready, no AGPL dependencies.

---

## PART 2: FEATURE GAP ANALYSIS

### Features MiroFish HAS That We Must Match

| Feature | MiroFish Implementation | SwarmScope Status |
|---------|------------------------|-------------------|
| Source document upload (PDF/MD/TXT) | Home.vue file upload zone | ✅ In build prompt |
| Knowledge graph visualization | GraphPanel.vue with D3 | ⚠️ Not in build prompt — ADD |
| Agent persona generation from source | oasis_profile_generator.py | ✅ In build prompt (agent_generator.py) |
| Agent profile cards (personality, topics, bio) | Step2EnvSetup.vue | ✅ In build prompt |
| Dual-platform simulation | run_parallel_simulation.py | ❌ Not needed — we're domain-agnostic |
| Real-time simulation timeline | Step3Simulation.vue timeline feed | ✅ In build prompt (Live Dashboard) |
| Agent chat (in-character) | Step5Interaction.vue | ✅ In build prompt (Agent Chat) |
| Report generation with tools | report_agent.py (ReACT pattern) | ⚠️ Partially — ADD tool-augmented reporting |
| Survey/batch agent interviews | Step5Interaction survey tab | ⚠️ Not in build prompt — ADD |
| i18n / multi-language | Vue-i18n (zh/en) | ❌ Not for MVP |
| Project history dashboard | HistoryDatabase.vue | ⚠️ Not in build prompt — ADD |

### Features SwarmScope HAS That MiroFish Lacks

| Feature | SwarmScope | MiroFish |
|---------|-----------|----------|
| **Event-sourced replay** | Every tick stored as snapshot, deterministic replay | No replay, no snapshots |
| **Deterministic rules before LLM** | Rule engine resolves non-negotiable mechanics first | Everything goes to LLM |
| **Relevance-based activation** | Score by relevance/tension/goal proximity | Random probability + time-of-day only |
| **3-layer memory** | Working/episodic/semantic with embedding retrieval | Append-only Zep episodes |
| **Mid-simulation interventions** | inject_event, modify_agent, modify_world | Post-simulation interviews only |
| **Editable world model** | World Editor screen with inline editing | No editing after extraction |
| **Explicit KPIs** | Defined at world compilation, tracked per tick | No KPI concept |
| **Cost budget controls** | Per-run USD cap, rate limiting, token tracking | No controls, just a warning |
| **Domain-agnostic actions** | form_alliance, reallocate_resource, etc. | Twitter/Reddit actions only |
| **Pause/resume** | Full simulation lifecycle management | Must complete or kill |
| **Random seed control** | Seeded randomness for reproducibility | No seeding found |
| **PostgreSQL + Redis** | Production-grade persistence | SQLite + JSON files |
| **WebSocket streaming** | Real-time tick events via WS | Polling-based status checks |
| **Influence graph** | Tracked and visualized per tick | No agent-to-agent influence tracking |

---

## PART 3: FEATURES TO ADD TO SWARMSCOPE

Based on the analysis, here are features we should add to the build prompt that would make SwarmScope strictly superior:

### 3.1 Knowledge Graph Visualization (from MiroFish)

MiroFish's GraphPanel is a real strength — users see their extracted world as an interactive graph.

**Add to SwarmScope:**
- After world compilation, render entities/factions/tensions as an interactive force-directed graph
- Use D3.js within Angular (or ngx-graph)
- Nodes = entities + factions, edges = relationships + tensions
- Clickable nodes open edit panels
- Graph updates live during simulation as relationships change

**Where in build prompt:** Add to World Editor screen AND Live Dashboard screen.

### 3.2 Tool-Augmented Report Generation (from MiroFish)

MiroFish's ReACT report agent with 4 tools is well-designed.

**Add to SwarmScope:**
- Report worker should use Gemini function calling with these tools:
  1. `query_tick_data(tick_range, filters)` — retrieve specific tick events
  2. `analyze_kpi_trajectory(kpi_name)` — compute trend analysis on a KPI
  3. `compare_agent_outcomes(agent_ids)` — cross-agent comparison
  4. `interview_agent(agent_id, question)` — post-sim agent interview via Gemini
  5. `find_causal_chain(event_id)` — trace cause-effect chain through tick events
- Max 5 tool calls per report section
- Show tool usage log in the Report Viewer UI

### 3.3 Survey / Batch Agent Interview (from MiroFish)

MiroFish's Step 5 has a survey feature for mass-questioning agents.

**Add to SwarmScope:**
- Survey endpoint: `POST /simulations/{id}/survey` with `{question, target_agent_ids, response_format}`
- Batch Gemini calls to selected agents (or all chat-enabled agents)
- Aggregate responses: sentiment distribution, keyword extraction, consensus analysis
- Display results as charts in Agent Chat screen
- Useful for: "How do faction leaders feel about the new policy?" type queries

### 3.4 Project History / Scenario Library

MiroFish has a history dashboard showing all past projects.

**Add to SwarmScope:**
- Scenarios list page is already in the build prompt, but should include:
  - Status badges per stage (world compiled, agents generated, simulation completed, report generated)
  - Last run date, tick count, agent count
  - Quick "clone scenario" action for running variations
  - Search/filter by domain, date, status

### 3.5 Simulation Comparison View (MiroFish Lacks This Too)

Neither product has this, but it's a killer feature for a forecasting tool.

**Add to SwarmScope:**
- `GET /simulations/compare?ids=uuid1,uuid2` — compare two simulation runs
- Side-by-side KPI trajectories
- Diff view: what changed between runs (different interventions, different seeds)
- Highlight divergence points: "At tick 7, outcome X diverged because of intervention Y"
- This is the "explore plausible futures under explicit assumptions" promise made real

### 3.6 Branching Simulations / Fork from Snapshot

MiroFish has no rollback or branching. This is a major opportunity.

**Add to SwarmScope:**
- From any tick snapshot, user can "fork" a new simulation run
- New run starts from that tick's world state with optional modifications
- Enables: "What if we had intervened at tick 5 instead of tick 10?"
- Database: `simulation_runs.forked_from_tick_id UUID REFERENCES ticks(id)`
- UI: Timeline shows branch points as fork icons

### 3.7 Agent Influence Tracking (MiroFish Lacks This)

MiroFish has no concept of agent-to-agent influence.

**Add to SwarmScope:**
- Every agent action that targets another agent creates an influence edge
- Track: `{source_agent, target_agent, action_type, tick, weight}`
- Accumulate weights over simulation run
- Influence graph updates live on the dashboard
- Report includes influence analysis: "Agent X had the most impact because..."

### 3.8 Determinism Audit Log

MiroFish runs are non-reproducible. Make SwarmScope's reproducibility a visible feature.

**Add to SwarmScope:**
- Every tick log records: `{random_seed_state, gemini_call_hash, rule_results, stochasticity_source}`
- When Gemini gives a different response on replay (it will), log: "Stochasticity entered at tick 7, agent X decision"
- UI: "Determinism Report" tab in Report Viewer showing where randomness affected outcomes
- This is the auditability promise — enterprise buyers will love this

### 3.9 Export / API Integration

Neither product has this well.

**Add to SwarmScope:**
- Export report as PDF (from Report Viewer)
- Export tick data as CSV/JSON
- Export influence graph as GEXF (for Gephi)
- Webhook notifications: POST to user-defined URL on simulation complete
- API key auth for programmatic access

### 3.10 Authentication & Multi-Tenancy (MiroFish Has Neither)

MiroFish has zero auth (Issue #487). Build this from day one.

**Add to SwarmScope:**
- JWT-based auth with FastAPI security
- User model: `users` table with email, hashed password, API key
- All scenarios/simulations scoped to user
- Rate limiting per user
- Admin dashboard for user management (post-MVP)

---

## PART 4: UPDATED ARCHITECTURE ADDITIONS

### New Database Tables

```sql
-- Add to existing schema

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add user_id FK to scenarios table
ALTER TABLE scenarios ADD COLUMN user_id UUID REFERENCES users(id);

-- Influence tracking
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

-- Simulation forking
ALTER TABLE simulation_runs ADD COLUMN forked_from_tick_id UUID REFERENCES ticks(id);

-- Survey results
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

### New API Endpoints

```
# Auth
POST   /auth/register
POST   /auth/login
POST   /auth/refresh

# Surveys
POST   /simulations/{id}/survey
GET    /simulations/{id}/surveys
GET    /simulations/{id}/surveys/{sid}

# Comparison
GET    /simulations/compare?ids=uuid1,uuid2

# Forking
POST   /simulations/{id}/fork-from-tick/{tick_id}

# Influence
GET    /simulations/{id}/influence-graph
GET    /simulations/{id}/influence-graph/agent/{aid}

# Export
GET    /simulations/{id}/export/report?format=pdf
GET    /simulations/{id}/export/ticks?format=csv
GET    /simulations/{id}/export/influence?format=gexf

# Knowledge Graph
GET    /scenarios/{id}/knowledge-graph       # D3-compatible nodes+edges
```

### New Frontend Components

```
frontend/src/app/
├── features/
│   ├── auth/
│   │   ├── login.component.ts
│   │   └── register.component.ts
│   ├── scenario-library/
│   │   └── scenario-library.component.ts     # History + clone + filter
│   ├── knowledge-graph/
│   │   └── knowledge-graph.component.ts      # D3 force-directed graph
│   ├── simulation-compare/
│   │   └── simulation-compare.component.ts   # Side-by-side KPI + diff
│   └── survey/
│       └── survey.component.ts               # Batch agent surveys
├── shared/components/
│   ├── influence-graph/                      # Already planned
│   ├── knowledge-graph-viewer/               # NEW: D3 entity/faction graph
│   ├── determinism-audit/                    # NEW: Stochasticity report
│   └── export-menu/                          # NEW: Export options dropdown
```

### New Engine Files

```
backend/app/engine/
├── influence_tracker.py      # Track agent-to-agent influence edges per tick
├── fork_manager.py           # Create forked simulation from tick snapshot
├── survey_executor.py        # Batch agent surveys via Gemini
└── determinism_auditor.py    # Track where stochasticity entered
```

---

## PART 5: THE 12 DIFFERENTIATORS (VERIFIED)

Based on reading MiroFish's actual code, here are the 12 concrete ways SwarmScope is different. Each is verified against MiroFish's codebase:

| # | Differentiator | MiroFish Reality (with evidence) | SwarmScope Approach |
|---|---------------|----------------------------------|-------------------|
| 1 | **Own engine** | Wrapper around OASIS (AGPL) — `run_reddit_simulation.py:577` | Custom tick engine, no external dependency |
| 2 | **Domain-agnostic** | Hardcoded Twitter/Reddit actions — `config.py`, Issue #476 | Pluggable action types per domain |
| 3 | **Event-sourced replay** | Snapshot-only, no replay — `simulation_manager.py:145` | Every tick stored with full snapshot, fork from any point |
| 4 | **Deterministic seeding** | No `random.seed()` found — `run_reddit_simulation.py:21-24` | Seeded random throughout, stochasticity audit log |
| 5 | **Relevance-based activation** | Random probability + time-of-day — `run_reddit_simulation.py:469-521` | Score by relevance, tension, goal proximity |
| 6 | **Rule engine before LLM** | Everything goes to OASIS LLM — no rule layer found | Deterministic rules resolve first, LLM only for ambiguity |
| 7 | **3-layer memory** | Append-only Zep episodes — `zep_graph_memory_updater.py:24-62` | Working/episodic/semantic with embedding retrieval |
| 8 | **Mid-run interventions** | Post-simulation interviews only — `run_reddit_simulation.py:214-298` | 3 types during active simulation + fork from any tick |
| 9 | **Editable world model** | No edit UI found in any frontend component | Full World Editor with inline editing before and during run |
| 10 | **Explicit KPIs** | No KPI concept in codebase | Defined at extraction, tracked per tick, visualized live |
| 11 | **Cost controls** | No budget, no rate limiting — only a warning in .env | Per-run USD cap, rate limiter, token tracking, cost dashboard |
| 12 | **Production-grade** | 4 critical CVEs unpatched, no auth, SQLite — Issues #483,487,488,489 | PostgreSQL, JWT auth, FastAPI, proper error handling |

---

## PART 6: PRIORITY ORDER FOR ADDITIONS

### Must-Have for MVP (add to build prompt now)

1. **Knowledge graph visualization** — users need to see what was extracted
2. **Tool-augmented reporting** — match MiroFish's ReACT quality
3. **JWT authentication** — cannot demo without basic auth
4. **Scenario library page** — users need to see past work
5. **Influence tracking** — core to the "influence graph" promise in report

### Should-Have for v1.1

6. **Survey/batch interview** — powerful for enterprise demos
7. **Simulation comparison** — the "explore plausible futures" killer feature
8. **Fork from tick** — makes replay actionable, not just viewable
9. **Export (PDF, CSV, GEXF)** — enterprise buyers expect this

### Nice-to-Have for v1.2

10. **Determinism audit log** — unique trust feature
11. **Webhook notifications** — API integration story
12. **i18n** — if targeting international markets
