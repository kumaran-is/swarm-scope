# Session 9: Integration Testing & Polish (Phase 13)

> **Pre-requisite**: Sessions 1-8 complete. All features implemented.
> **Goal**: Full end-to-end tested, error handling polished, cost dashboard added, README written.
> **Estimated time**: 20-30 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context.

Now execute **Phase 13 (Integration & Polish)** — the final phase.

### Phase 13: Integration & Polish (Steps 71-74)

71. **Full end-to-end integration test**:

    Write a test script (or do it manually) that exercises the COMPLETE user journey:

    ```
    1.  Register a new user → POST /auth/register
    2.  Login → POST /auth/login → get JWT token
    3.  Upload a source document (use a sample policy document, 2-3 pages)
        → POST /scenarios (multipart with file)
    4.  Compile world model → POST /scenarios/{id}/compile → wait for completion
    5.  View world model → GET /scenarios/{id}/world → verify entities, factions, KPIs
    6.  Edit world model → PUT /scenarios/{id}/world → change an entity name
    7.  View knowledge graph → GET /scenarios/{id}/knowledge-graph → verify D3 nodes/edges
    8.  Generate agents (20 agents for testing) → POST /scenarios/{id}/generate-agents → wait
    9.  Start simulation (5 ticks) → POST /simulations → connect WebSocket
    10. Verify WebSocket receives tick_complete events for ticks 1-5
    11. Mid-simulation: inject event intervention → POST /simulations/{id}/interventions
    12. Verify intervention applied at next tick
    13. Fork from tick 3 → POST /simulations/{id}/fork-from-tick/{tick_3_id}
    14. Verify forked simulation starts from tick 3 state and continues
    15. Chat with an agent → POST /simulations/{id}/agents/{aid}/chat → get in-character response
    16. Run a survey → POST /simulations/{id}/survey → verify aggregate results
    17. Generate report → POST /simulations/{id}/report → wait for completion
    18. Verify report has: executive summary, timeline, influence graph, KPI trajectories, tool usage log
    19. Run ensemble (size 3, 5 ticks each) → POST /ensembles
    20. Verify ensemble statistics: KPI means, confidence intervals, robustness score
    21. Configure webhook ingestion source → POST /scenarios/{id}/ingestion-sources
    22. Send test webhook → POST /webhooks/ingest/{source_id} → verify intervention created
    23. View scenario library → GET /scenarios → verify all scenarios visible with correct status
    ```

    If any step fails, fix the issue before proceeding. Document any bugs found and their fixes.

72. **Add error handling, loading states, and toast notifications throughout**:

    **Backend:**
    - Add global exception handler in `main.py`:
      ```python
      @app.exception_handler(Exception)
      async def global_exception_handler(request, exc):
          # Log full traceback
          # Return structured error response: {error: str, detail: str, status_code: int}
      ```
    - Add specific handlers for: `HTTPException`, `ValidationError`, `GeminiError`, `DatabaseError`
    - All background tasks (simulation, report, ensemble) must catch exceptions and update status to `failed` with error message

    **Frontend:**
    - Add a toast notification service (`shared/services/toast.service.ts`):
      - Success (green), Error (red), Warning (yellow), Info (blue)
      - Auto-dismiss after 5 seconds
      - Stack up to 3 toasts
    - Add loading states to ALL async operations:
      - "Compiling world model..." with spinner
      - "Generating agents..." with progress (X/N)
      - "Starting simulation..." 
      - "Generating report..." with section progress
      - "Running ensemble..." with run progress (X/N completed)
    - Error states: if any API call fails, show toast with error message. If WebSocket disconnects, show reconnecting indicator.
    - Empty states: for all lists (scenarios, agents, ticks, interventions) show meaningful empty state messages

73. **Add cost tracking dashboard**:

    **Backend:**
    - Add a cost tracking utility (`backend/app/utils/cost_tracker.py`):
      ```python
      class CostTracker:
          # Gemini pricing (configurable via env):
          PRICE_PER_1K_INPUT_TOKENS = 0.00125   # Gemini 2.5 Pro
          PRICE_PER_1K_OUTPUT_TOKENS = 0.005
          
          def log_call(self, simulation_run_id, purpose, input_tokens, output_tokens):
              # Store in Redis hash: cost:{simulation_run_id}
              pass
          
          def get_run_cost(self, simulation_run_id) -> dict:
              # Return {total_calls, total_input_tokens, total_output_tokens, estimated_cost_usd}
              pass
          
          def get_ensemble_cost(self, ensemble_run_id) -> dict:
              # Sum across all child runs
              pass
      ```
    - Integrate with Gemini client: every call logs to cost tracker
    - New endpoint: `GET /api/v1/simulations/{id}/cost` → returns cost breakdown
    - New endpoint: `GET /api/v1/ensembles/{id}/cost` → returns ensemble cost breakdown

    **Frontend:**
    - Add cost indicator to Live Dashboard header: "Cost so far: $0.042 (89 Gemini calls)"
    - Add cost summary to Report Viewer
    - Add cost summary to Ensemble Viewer (already spec'd in Session 7)
    - Add cost column to Scenario Library cards

74. **Write README**:

    Create `README.md` at the monorepo root with:

    - Project name, one-line description, screenshot placeholder
    - Key features list (12 differentiators from the MiroFish analysis)
    - Tech stack summary
    - Prerequisites (Docker, Node 22+, Python 3.14, Gemini API key)
    - Quick start:
      ```
      cp .env.example .env
      # Edit .env with your GEMINI_API_KEY
      docker-compose up --build
      # Open http://localhost:4200
      ```
    - Architecture overview (tick loop diagram, 3-layer memory, selective activation)
    - API documentation link (FastAPI auto-generates at /docs)
    - Environment variables reference
    - Development setup (running backend and frontend separately for hot reload)
    - MVP scope and limitations
    - License placeholder

### Final Verification

Run through the full application one more time as a real user would:

- [ ] Open browser → register → login
- [ ] Upload a real document (find a short policy brief or news article)
- [ ] Compile world → review and edit entities → generate 50 agents
- [ ] Run 10-tick simulation → watch live dashboard
- [ ] Inject an intervention at tick 5 → observe impact
- [ ] Fork from tick 3 → see different outcome
- [ ] Chat with an agent → get coherent in-character response
- [ ] Run survey on 5 agents → see aggregate sentiment
- [ ] Generate report → read all sections → see tool usage log
- [ ] Run 3-run ensemble → see confidence bands and robustness score
- [ ] Check cost dashboard → verify numbers are reasonable
- [ ] Everything renders without console errors
- [ ] All API calls return proper error messages on invalid input

**The application is now complete. Ship it.**
