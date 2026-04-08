# Session 4: API Endpoints + Full Frontend (Phases 5-6)

> **Pre-requisite**: Sessions 1-3 complete. Engine runs a 5-agent, 3-tick simulation successfully.
> **Goal**: Full REST API + WebSocket endpoint + all 7 Angular screens working. Upload a document in the browser → see simulation results on the dashboard.
> **Estimated time**: 30-40 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. Pay attention to **Section 5 (API Endpoints)** and **Section 6 (Angular 21 Frontend)**.

Now execute **Phase 5 (API)** and **Phase 6 (Frontend)**. These go together because the frontend needs the API to function.

### Phase 5: API (Steps 28-31)

28. **Implement all REST endpoints** in `backend/app/api/`:

    **`scenarios.py`**:
    ```
    POST   /api/v1/scenarios                    # Create scenario + upload source file (multipart)
    GET    /api/v1/scenarios                    # List all scenarios
    GET    /api/v1/scenarios/{id}               # Get scenario details
    PUT    /api/v1/scenarios/{id}               # Update scenario config
    DELETE /api/v1/scenarios/{id}               # Delete scenario + cascade
    POST   /api/v1/scenarios/{id}/compile       # Trigger world compilation (background task)
    POST   /api/v1/scenarios/{id}/generate-agents  # Generate agent population (background task)
    ```

    **`world.py`**:
    ```
    GET    /api/v1/scenarios/{id}/world         # Get compiled world model
    PUT    /api/v1/scenarios/{id}/world         # Edit world model (user corrections)
    GET    /api/v1/scenarios/{id}/knowledge-graph  # D3-compatible {nodes, edges}
    ```

    **`simulation.py`**:
    ```
    POST   /api/v1/simulations                  # Create + start simulation run
    GET    /api/v1/simulations/{id}             # Get status + current tick
    POST   /api/v1/simulations/{id}/pause       # Pause
    POST   /api/v1/simulations/{id}/resume      # Resume
    POST   /api/v1/simulations/{id}/stop        # Stop early
    GET    /api/v1/simulations/{id}/ticks       # All tick data (paginated)
    GET    /api/v1/simulations/{id}/ticks/{n}   # Specific tick snapshot
    ```

    **`interventions.py`**:
    ```
    POST   /api/v1/simulations/{id}/interventions        # Create intervention
    GET    /api/v1/simulations/{id}/interventions         # List interventions
    DELETE /api/v1/simulations/{id}/interventions/{iid}   # Cancel pending
    ```

    **`agents.py`**:
    ```
    GET    /api/v1/simulations/{id}/agents               # List all agents
    GET    /api/v1/simulations/{id}/agents/{aid}          # Agent detail + memory
    POST   /api/v1/simulations/{id}/agents/{aid}/chat     # Chat with agent (Gemini-powered)
    ```

    **`reports.py`**:
    ```
    POST   /api/v1/simulations/{id}/report      # Generate report (background task)
    GET    /api/v1/simulations/{id}/report       # Get generated report
    ```

    **`router.py`** — aggregate all sub-routers under `/api/v1` prefix.

    For all background tasks (compile, generate-agents, start simulation, generate report), use FastAPI `BackgroundTasks` or Redis-based task queue. Return task status immediately with a polling endpoint or use WebSocket for progress.

29. **Implement WebSocket endpoint** in `backend/app/api/ws.py`:
    ```
    WS /api/v1/ws/simulations/{id}
    ```
    - On connect: validate simulation exists, add to subscriber list
    - Broadcast messages typed as:
      ```json
      {
        "type": "tick_complete | agent_action | kpi_update | intervention_applied | simulation_complete | error",
        "tick": 5,
        "data": { ... }
      }
      ```
    - Auto-clean disconnected clients
    - Use Redis pub/sub as message bus between simulation worker and WebSocket handler

30. **Implement simulation worker** (`backend/app/workers/simulation_worker.py`):
    - Wraps `SimulationOrchestrator.run_simulation()` as a background task
    - Updates `simulation_runs.status` as it progresses
    - Publishes tick events to Redis pub/sub channel `simulation:{id}:ticks`
    - Handles pause/resume via Redis key `simulation:{id}:control`
    - On error: set status to `failed`, log error, notify WebSocket

31. **Implement report worker** (`backend/app/workers/report_worker.py`):
    - Loads all tick data, KPI trajectories, intervention log
    - Calls Gemini with report planning prompt → gets outline
    - For each section: calls Gemini with section prompt
    - Saves final report to `reports` table
    - Notifies via WebSocket: `{"type": "report_ready"}`

### Phase 6: Frontend (Steps 32-40)

32. **Create all services** in `frontend/src/app/core/services/`:
    - `api.service.ts` — HttpClient wrapper with base URL config
    - `websocket.service.ts` — Native WebSocket with auto-reconnect, Signal-based state
    - `scenario.service.ts` — CRUD calls for scenarios
    - `simulation.service.ts` — Start/pause/resume/stop + tick polling
    - `intervention.service.ts` — Create/list interventions
    - `report.service.ts` — Generate/fetch reports
    - Add `error.interceptor.ts` for global HTTP error handling

33. **Create shared components** in `frontend/src/app/shared/components/`:
    - `file-upload/` — Drag-and-drop file upload (PDF, DOCX, TXT, MD)
    - `agent-card/` — Agent display card (name, role, faction, status, mood)
    - `tick-timeline/` — Horizontal scrollable timeline of completed ticks
    - `kpi-gauge/` — Real-time gauge/chart for a single KPI
    - `influence-graph/` — D3 force-directed graph of agent influence
    - `knowledge-graph-viewer/` — D3 force-directed graph of entities/factions/tensions

34. **Build Scenario Intake screen** (`scenario-intake.component.ts`):
    - File upload zone (drag-and-drop)
    - Name, description, domain selector (policy, org_change, crisis, market, fiction)
    - Config panel: max agents slider (10-100), max ticks slider (5-30), random seed input
    - "Compile World" button → POST /compile → show progress → navigate to World Editor

35. **Build World Editor screen** (`world-editor.component.ts`):
    - Knowledge graph visualization (D3 force-directed) in left panel
    - Right panel: editable cards for summary, entities table, factions cards, resources table, constraints list, tensions list, KPIs table
    - "Regenerate" button per section
    - "Generate Agents" button → POST → navigate to Simulation Control

36. **Build Simulation Control screen** (`simulation-control.component.ts`):
    - Agent population grid (agent cards)
    - Config review panel
    - Start / Pause / Resume / Stop buttons
    - Progress: current tick / max ticks
    - Links to Dashboard, Intervention Console, Agent Chat

37. **Build Live Dashboard screen** (`live-dashboard.component.ts`) — WebSocket-powered:
    - Tick Timeline (horizontal scrollable)
    - KPI Gauges (real-time updating charts — use D3 or ngx-charts)
    - Active Agents Panel (who's acting this tick)
    - Event Feed (scrolling log)
    - World State Summary (resource levels, faction power bars)
    - Influence Graph (D3 force-directed, updates per tick)
    - All data from WebSocket, rendered via Signals

38. **Build Intervention Console screen** (`intervention-console.component.ts`):
    - 3 intervention type cards:
      1. Inject Event: text area + severity selector + entity multi-select
      2. Modify Agent: agent dropdown + editable fields
      3. Modify World: resource/KPI selector + new value
    - "Fire at next tick" button
    - Intervention history log with status badges

39. **Build Agent Chat screen** (`agent-chat.component.ts`):
    - Left sidebar: top 10 chat-enabled agents with name, role, mood indicator
    - Main panel: chat interface
    - Agent responds in-character via Gemini
    - Collapsible side panel: agent's current goals, resources, alliances

40. **Build Report Viewer screen** (`report-viewer.component.ts`):
    - Executive Summary section
    - Timeline: vertical timeline of key events
    - Influence Graph: interactive D3 final network
    - KPI Trajectories: line charts with intervention markers
    - Key Findings: numbered findings with evidence + confidence scores
    - Counterfactual Notes section

**All components must be standalone** (no NgModules). Use Angular Signals for state. Use `@if`, `@for`, `@switch` control flow. Lazy-load all feature components via router.

### Verification Checklist

Full end-to-end test:

- [ ] Open `http://localhost:4200` → Scenario Intake screen loads
- [ ] Upload a PDF/TXT file → file appears in upload zone
- [ ] Fill name, domain, config → click "Compile World"
- [ ] World Editor loads with extracted entities, factions, KPIs
- [ ] Edit an entity name → save → verify it persists
- [ ] Click "Generate Agents" → Simulation Control shows agent cards
- [ ] Click "Start" → Live Dashboard updates in real-time via WebSocket
- [ ] See tick events, KPI gauges updating, agents acting
- [ ] Open Intervention Console → inject an event → see it applied next tick
- [ ] Open Agent Chat → select an agent → send message → get in-character response
- [ ] Simulation completes → click "Generate Report" → Report Viewer shows full report
- [ ] Influence graph renders with agent nodes and weighted edges

**STOP after verification. Do not proceed to Phase 7.**
