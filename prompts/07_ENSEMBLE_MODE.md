# Session 7: Ensemble Mode — Multi-Run Statistics (Phase 11)

> **Pre-requisite**: Sessions 1-6 complete. Full simulation lifecycle works including forking.
> **Goal**: Run same scenario N times with different seeds, aggregate results, show statistical confidence bands and robustness scores.
> **Estimated time**: 20-25 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. Pay attention to **Section 10.8 (Ensemble Mode)** which contains the complete spec for this feature.

Now execute **Phase 11 (Ensemble Mode)** only.

### Phase 11: Ensemble Mode (Steps 56-61)

56. **Implement `ensemble_runs` table** — The migration was already created in Session 1. Now ensure the ORM model in `backend/app/models/ensemble.py` is complete:
    - Fields: id, scenario_id, user_id, ensemble_size, base_config (JSONB), status, statistics (JSONB), created_at, completed_at
    - Relationship to `simulation_runs` via `ensemble_run_id` FK

57. **Implement ensemble runner** (`backend/app/engine/ensemble_runner.py`):
    ```python
    class EnsembleRunner:
        MAX_PARALLEL_RUNS = 3  # Don't overwhelm Gemini API
        
        async def run_ensemble(self, scenario_id: UUID, ensemble_size: int, base_config: dict, user_id: UUID) -> EnsembleRun:
            # 1. Create ensemble_run record (status='running')
            # 2. Generate N deterministic seeds: Random(base_seed).randint(0, 2**32) × N
            # 3. For each seed: create simulation_run with ensemble_run_id + ensemble_seed_index
            # 4. Execute runs with asyncio.Semaphore(MAX_PARALLEL_RUNS):
            #    async with sem:
            #        await orchestrator.run_simulation(run)
            # 5. After all complete (or partial if some fail):
            #    await self.aggregate_results(ensemble_run_id)
            # 6. Update ensemble status to 'completed'
            pass
        
        def _generate_seeds(self, base_seed: int, count: int) -> list[int]:
            rng = random.Random(base_seed)
            return [rng.randint(0, 2**32 - 1) for _ in range(count)]
    ```

    - Handle partial failures: if 1 of 5 runs fails, mark it as failed but continue others. Compute statistics from completed runs with a warning.
    - Track progress: update `ensemble_runs` record periodically with how many runs completed.

58. **Implement ensemble aggregator** (`backend/app/engine/ensemble_aggregator.py`):
    ```python
    import numpy as np
    
    class EnsembleAggregator:
        async def aggregate(self, ensemble_run_id: UUID) -> dict:
            # Load all completed simulation_runs for this ensemble
            # Load all ticks for each run
            # Return statistics dict
            pass
        
        def aggregate_kpis(self, all_runs_kpi_data) -> dict:
            """
            For each KPI, for each tick:
            - mean = np.mean(values_across_runs)
            - std = np.std(values_across_runs)
            - min, max = np.min(), np.max()
            - ci_95_low = mean - 1.96 * std / sqrt(n)
            - ci_95_high = mean + 1.96 * std / sqrt(n)
            
            Also compute final-tick statistics.
            """
            pass
        
        def aggregate_influence(self, all_runs_influence_data) -> dict:
            """
            For each agent pair (source, target):
            - mean_weight across runs
            - variance of weight
            - Classify as 'stable' (variance < 1.0) or 'volatile' (variance >= 1.0)
            """
            pass
        
        def compute_robustness_score(self, kpi_stats) -> float:
            """
            Robustness = 1 - (mean normalized KPI variance across all KPIs)
            
            Normalized variance = std / abs(mean) for each KPI at final tick
            Average across all KPIs, subtract from 1.
            Score 0-1: 1.0 = perfectly consistent, 0.0 = wildly variable
            """
            pass
        
        def find_divergence_point(self, kpi_stats) -> int:
            """
            Find earliest tick where inter-run KPI variance exceeds 2x the initial variance.
            This is approximately where "interesting stuff starts happening differently."
            """
            pass
        
        def generate_run_summaries(self, runs_data) -> list[dict]:
            """
            For each run: {run_index, seed, final_kpis, key_event}
            key_event = the single most impactful event (highest KPI delta in any tick)
            """
            pass
    ```

59. **Implement ensemble API endpoints**:
    ```
    POST   /api/v1/ensembles                          # {scenario_id, ensemble_size, base_config}
    GET    /api/v1/ensembles                          # List user's ensembles
    GET    /api/v1/ensembles/{id}                     # Status + statistics
    GET    /api/v1/ensembles/{id}/runs                # List child simulation runs
    GET    /api/v1/ensembles/{id}/statistics           # Aggregated statistics only
    GET    /api/v1/ensembles/{id}/kpi/{kpi_name}      # Detailed per-KPI data: all runs + aggregate
    DELETE /api/v1/ensembles/{id}                     # Cancel or delete
    ```

    Add schemas: `EnsembleCreateRequest`, `EnsembleResponse`, `EnsembleStatisticsResponse`, `KPIEnsembleDetailResponse`

60. **Build ensemble viewer Angular component** (`frontend/src/app/features/ensemble-viewer/`):

    Route: `/ensembles/{id}`

    **Section 1: Robustness Summary Card**
    - Large robustness score as a percentage gauge (0-100%)
    - Divergence tick number with label "Runs diverge at tick X"
    - Two badges: "Most stable: {kpi_name}" and "Most variable: {kpi_name}"
    - Ensemble size and completed runs count (e.g., "5/5 runs completed")

    **Section 2: KPI Confidence Band Charts**
    - One chart per KPI (tab-switchable)
    - X-axis: ticks (1 to max_ticks)
    - Bold dark line: mean trajectory
    - Shaded band (light fill): 95% confidence interval (ci_95_low to ci_95_high)
    - Thin semi-transparent lines: individual run trajectories (toggleable)
    - Use D3 area charts with smooth interpolation
    - Intervention markers as vertical dashed lines (if any interventions were applied)

    **Section 3: Influence Stability Heatmap**
    - Matrix heatmap: rows = source agents, columns = target agents
    - Cell color: green gradient = stable (low variance), red gradient = volatile (high variance)
    - Cell size proportional to mean weight
    - Hover tooltip: "Agent A → Agent B: mean weight 3.2 ± 0.4 (stable)" or "± 2.8 (volatile)"

    **Section 4: Run Comparison Table**
    - Columns: Run #, Seed, each KPI final value, Key Event
    - Rows: one per simulation run
    - Click row → navigate to `/simulations/{run_id}/dashboard`
    - Sortable by any column
    - Highlight row with best/worst outcome per KPI

    **Section 5: Cost Summary**
    - Total Gemini calls across all runs
    - Total tokens used (input + output)
    - Estimated total cost

61. **Add "Run Ensemble" button to Simulation Control screen**:
    - Place next to "Start Simulation" button
    - Opens modal:
      - Ensemble size slider (2-10, default 5)
      - Estimated cost display: `{ensemble_size} × ${estimated_single_run_cost} = ${total}`
      - Warning text: "This will run {N} simulations. Estimated cost: ${X}."
      - "Confirm & Run Ensemble" button
    - After launch: navigate to `/ensembles/{id}` to watch progress

### Verification Checklist

Test with a small scenario (10 agents, 5 ticks) to keep costs low:

- [ ] Create ensemble with size 3 → 3 simulation runs created with different seeds
- [ ] All 3 runs execute (check: 3 entries in simulation_runs with this ensemble_run_id)
- [ ] After completion: statistics JSONB populated in ensemble_runs
- [ ] KPI statistics show mean, std, CI for each tick
- [ ] Robustness score is between 0 and 1
- [ ] Influence statistics classify relationships as stable/volatile
- [ ] Ensemble viewer: robustness gauge renders correctly
- [ ] KPI confidence band chart shows mean line + shaded CI + individual run lines
- [ ] Influence heatmap renders with green/red coloring
- [ ] Run comparison table shows all runs, click navigates to individual dashboard
- [ ] Partial failure: kill one run mid-execution → ensemble still completes with 2/3 runs + warning

**STOP after verification. Do not proceed to Phase 12.**
