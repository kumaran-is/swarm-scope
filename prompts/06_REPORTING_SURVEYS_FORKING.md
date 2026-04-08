# Session 6: Enhanced Reporting + Surveys + Forking + Scenario Library (Phases 9-10)

> **Pre-requisite**: Sessions 1-5 complete. Auth works, knowledge graph renders, influence tracked.
> **Goal**: Tool-augmented reports, batch surveys, fork-from-tick, scenario library.
> **Estimated time**: 25-30 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. Pay attention to **Sections 10.3 (Tool-Augmented Reporting)**, **10.5 (Scenario Library)**, **10.6 (Surveys)**, and **10.7 (Forking)**.

Now execute **Phase 9 (Enhanced Reporting & Surveys)** and **Phase 10 (Forking & Scenario Library)**.

### Phase 9: Enhanced Reporting & Surveys (Steps 49-52)

49. **Upgrade report worker to use Gemini function calling with 5 report tools**:

    Update `backend/app/workers/report_worker.py`. Define 5 tools as Gemini function declarations:

    - `query_tick_data(tick_start: int, tick_end: int, filters: dict)` → queries `ticks` table, returns events matching filters
    - `analyze_kpi_trajectory(kpi_name: str)` → loads KPI values across all ticks, computes trend (increasing/decreasing/stable), inflection points, rate of change
    - `compare_agent_outcomes(agent_ids: list[str])` → for each agent: starting vs final resources, goals achieved, key actions taken
    - `interview_agent(agent_id: str, question: str)` → makes a Gemini call with agent profile + memories + question, returns in-character answer
    - `find_causal_chain(event_description: str)` → searches tick events for related cause-effect sequences, returns chain

    **Report generation flow:**
    1. Planning call: Gemini receives `{world_model_summary, simulation_summary, kpi_final_values, total_ticks, intervention_log}` → outputs structured outline: `{sections: [{title, description, tools_to_use}]}`
    2. Per-section: Gemini writes section content. If it calls a tool, execute the tool, feed result back, let Gemini continue writing. Max 5 tool calls per section.
    3. Reflection: After all sections, one Gemini call reviews full report for consistency. Max 2 reflection rounds.
    4. Save to `reports` table.

50. **Add tool usage log to report output and Report Viewer UI**:
    - Store tool calls in `reports` table as new JSONB field: `tool_usage_log JSONB DEFAULT '[]'`
    - Each entry: `{section_index, tool_name, tool_input, tool_output_summary, timestamp}`
    - In Report Viewer: add collapsible "Research Log" section showing which tools were used per section

51. **Implement survey executor** (`backend/app/engine/survey_executor.py`):
    ```python
    class SurveyExecutor:
        async def run_survey(self, simulation_run_id, question, target_agent_ids, response_format) -> Survey:
            """
            1. Load each target agent's profile + memories + current world state
            2. For each agent: Gemini call with survey question, agent responds in-character
            3. Collect all responses
            4. Run aggregate analysis via one more Gemini call:
               - Sentiment distribution (positive/negative/neutral counts)
               - Key themes / keyword extraction
               - Consensus score (0-1, how much agents agree)
               - Notable outlier responses
            5. Save to surveys table
            """
    ```

    New endpoints:
    ```
    POST /api/v1/simulations/{id}/survey              # {question, target_agent_ids, response_format}
    GET  /api/v1/simulations/{id}/surveys              # List all surveys
    GET  /api/v1/simulations/{id}/surveys/{sid}         # Get survey detail + results
    ```

52. **Build survey UI in Agent Chat screen**:
    - Add a "Survey" tab alongside individual agent chat tabs
    - Survey form: question text area, agent multi-select (checkboxes), "All chat-enabled" toggle, response format (free text / yes-no / scale 1-5)
    - Submit → show loading with progress (X/N agents responded)
    - Results panel:
      - Sentiment pie chart
      - Key themes as tag cloud or list
      - Consensus score gauge
      - Individual responses in expandable cards (agent name + their answer)

### Phase 10: Forking & Scenario Library (Steps 53-55)

53. **Implement fork manager** (`backend/app/engine/fork_manager.py`):
    ```python
    class ForkManager:
        async def fork_from_tick(self, simulation_run_id, tick_id, new_config=None, interventions=None) -> SimulationRun:
            """
            1. Load the tick's snapshot from ticks table
            2. Create new simulation_run with:
               - forked_from_tick_id = tick_id
               - random_seed = new seed (or user-provided)
               - status = 'pending'
               - current_tick = original tick number
            3. Restore world state and agent states from snapshot
            4. If interventions provided, create intervention records for next tick
            5. Start simulation from restored state via simulation worker
            """
    ```

    New endpoint:
    ```
    POST /api/v1/simulations/{id}/fork-from-tick/{tick_id}
    Body: { "new_random_seed": optional, "interventions": optional list, "max_additional_ticks": optional }
    Response: { "new_simulation_run_id": "uuid", "forked_from_tick": 7 }
    ```

54. **Add Fork button to Tick Timeline component**:
    - Each tick in the timeline gets a small "fork" icon button
    - Clicking opens a modal:
      - Shows tick number and snapshot summary
      - Optional: new random seed (auto-generate or manual)
      - Optional: add interventions to apply at first tick of fork
      - Optional: max additional ticks to run
      - "Fork & Run" button
    - After fork: navigate to new simulation's dashboard
    - In the original simulation's dashboard, show fork indicators on the timeline

55. **Build scenario library component** (`frontend/src/app/features/scenario-library/scenario-library.component.ts`):
    - Replace the simple scenarios list at `/scenarios`
    - Card grid layout:
      - Each card shows: scenario name, domain badge, status pipeline (draft → compiled → agents → running → completed → reported)
      - Last run date, agent count, tick count
      - Click card → navigate to appropriate step based on status
    - Actions per card:
      - "Clone" → duplicate scenario + world model, navigate to new scenario's intake
      - "Delete" → confirm modal → cascade delete
    - Top bar: search by name, filter by domain dropdown, filter by status dropdown
    - Sort: by date (default), by name, by status
    - Empty state: "No scenarios yet. Create your first one."

### Verification Checklist

- [ ] Run a simulation → generate report → report shows tool usage log (which tools were called per section)
- [ ] Report contains interview quotes from agents (interview_agent tool was called)
- [ ] Report contains KPI trend analysis (analyze_kpi_trajectory tool was called)
- [ ] Submit a survey to 5 agents → all 5 respond → aggregate analysis shows sentiment + consensus
- [ ] Survey results display correctly in Agent Chat survey tab
- [ ] Open simulation dashboard → click fork icon on tick 3 → modal opens
- [ ] Fork with an intervention → new simulation starts from tick 3 state → intervention applied at tick 4
- [ ] Forked simulation produces different outcomes than original (due to new seed + intervention)
- [ ] Scenario library loads → shows all scenarios as cards → filter by domain works → search works
- [ ] Clone a scenario → new scenario appears with same world model → can modify independently

**STOP after verification. Do not proceed to Phase 11.**
