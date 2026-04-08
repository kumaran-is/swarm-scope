# Session 3: Core Simulation Engine (Phase 4)

> **Pre-requisite**: Sessions 1-2 complete. Gemini client works, extraction returns valid structured output.
> **Goal**: Working tick-based simulation engine. Can run a 5-agent, 3-tick test simulation end-to-end.
> **Estimated time**: 25-35 minutes (this is the hardest phase)

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. Pay special attention to **Section 3 (Core Engine — Tick Loop)** which defines the 10-step tick execution order.

Now execute **Phase 4 (Engine)** only. This is the heart of the system. Build each component carefully.

### Phase 4: Engine (Steps 18-27)

**Build in this exact order — each step depends on the one before it.**

18. **Implement world compiler** (`backend/app/engine/world_compiler.py`):
    - `compile_world(source_text: str) -> WorldModel` — calls Gemini extraction to convert raw text into structured world model
    - Validate output: at least 2 entities, at least 1 tension, at least 1 KPI
    - If validation fails, retry extraction once with a more explicit prompt
    - Save result to `world_models` table

19. **Implement agent generator** (`backend/app/engine/agent_generator.py`):
    - `generate_agents(world_model: WorldModel, count: int) -> list[Agent]` — calls Gemini to create agent population
    - Each agent gets: name, role, faction, personality (Big Five traits as floats 0-1), goals, initial resources
    - Mark top 10 agents by influence as `is_chat_enabled = True`
    - Initialize all memory layers: working_memory={}, episodic_memory=[], semantic_memory={}
    - Save all agents to `agents` table

20. **Implement activation scoring** (`backend/app/engine/activation.py`):
    ```python
    def compute_activation_scores(agents, world_state, current_tick, last_activated) -> list[tuple[Agent, float]]:
        """
        Score each agent 0.0-1.0:
        - relevance (0.3 weight): is agent's domain affected by recent events?
        - tension (0.25 weight): is agent in a high-conflict situation?
        - goal_proximity (0.25 weight): is agent close to achieving/failing a goal?
        - recency (0.15 weight): how long since agent was last activated? (longer = higher)
        - random_jitter (0.05 weight): small seeded random factor
        
        Return sorted list. Caller takes top K (default 15).
        """
    ```

21. **Implement rule engine** (`backend/app/engine/rule_engine.py`):
    - Define 5 rule types as a registry:
      - `resource_decay` — resources deplete by a configurable rate per tick
      - `alliance_maintenance` — alliance strength decreases by 0.1 per tick without interaction
      - `threshold_triggers` — if KPI crosses defined threshold, generate an event
      - `proximity_effects` — entities in same faction influence each other's resources
      - `scheduled_events` — events defined in world model that trigger at specific ticks
    - `apply_rules(world_state, agents, tick_number, random_gen) -> list[RuleOutcome]`
    - All rules use the seeded `random.Random` instance — never `random.random()`
    - Rules are deterministic: same input = same output

22. **Implement decision engine** (`backend/app/engine/decision_engine.py`):
    - `get_decisions(active_agents, world_state, memory_manager) -> list[AgentDecision]`
    - For each activated agent:
      1. Retrieve working memory + top 5 episodic memories (via embedding similarity)
      2. Build context: agent profile + memories + relevant world state
      3. Call Gemini function calling (via `gemini/decisions.py`)
      4. Parse result into `AgentDecision(agent_id, action, params, reasoning)`
    - If Gemini fails after retries, default to `do_nothing` with logged error
    - Run all Gemini calls concurrently with `asyncio.gather` (bounded by semaphore of 5)

23. **Implement state manager** (`backend/app/engine/state_manager.py`):
    - `apply_actions(world_state, decisions, rule_outcomes) -> WorldStateDelta`
    - Process all actions atomically:
      - Validate preconditions (e.g., can't form_alliance with self, can't reallocate more resources than owned)
      - Apply effects: update agent resources, relationships, faction standings
      - Compute world_state_delta (what changed this tick)
    - `take_snapshot(world_state, agents) -> dict` — serialize full state for replay
    - `restore_from_snapshot(snapshot: dict) -> tuple[WorldState, list[Agent]]` — for forking

24. **Implement memory manager** (`backend/app/engine/memory_manager.py`):
    Three-layer memory system:
    - `update_working_memory(agent, tick_events)` — set current tick context, clear previous
    - `add_episodic_memory(agent, tick, event_summary, emotional_valence, importance_score)` — append to episodic list
    - `compress_memories(agent)` — if episodic > 20 entries, summarize 5 least important via Gemini → merge into semantic memory
    - `retrieve_relevant_memories(agent, context, top_k=5)` — use embeddings to find most relevant episodic memories for decision context
    - `update_semantic_memory(agent, new_knowledge)` — merge compressed knowledge into long-term store

25. **Implement event log** (`backend/app/engine/event_log.py`):
    - Append-only log: `log_event(simulation_run_id, tick, event_type, agent_id, data)`
    - Event types: `agent_action`, `rule_outcome`, `intervention_applied`, `kpi_change`, `memory_compressed`, `gemini_call`, `error`
    - Store in `ticks.events` JSONB array
    - Never mutate past tick records

26. **Implement intervention handler** (`backend/app/engine/intervention_handler.py`):
    - `get_pending_interventions(simulation_run_id, tick_number) -> list[Intervention]`
    - `apply_intervention(intervention, world_state, agents) -> InterventionResult`
    - Three types:
      - `inject_event`: add event description to world state, notify all agents in working memory
      - `modify_agent`: update specific agent's goals, resources, or status
      - `modify_world`: change a resource level, constraint, or KPI value
    - Mark intervention as `applied` with `applied_at_tick`

27. **Implement orchestrator** (`backend/app/engine/orchestrator.py`) — THE MAIN TICK LOOP:
    ```python
    class SimulationOrchestrator:
        async def run_simulation(self, simulation_run: SimulationRun):
            random_gen = random.Random(simulation_run.random_seed)
            world_state = self.load_world_state(simulation_run.scenario_id)
            agents = self.load_agents(simulation_run.scenario_id)
            
            for tick in range(1, simulation_run.max_ticks + 1):
                # Check if paused or stopped
                if await self.check_pause_or_stop(simulation_run.id):
                    break
                
                tick_start = time.monotonic()
                
                # Step 0: Check external ingestion sources
                external_events = await self.ingestion_worker.check_sources(simulation_run.id, tick)
                
                # Step 1: Apply pending interventions
                interventions = await self.intervention_handler.apply_pending(simulation_run.id, tick)
                
                # Step 2: Score and select active agents
                scored = self.activation.compute_scores(agents, world_state, tick)
                active_agents = scored[:self.max_active_per_tick]  # default 15
                
                # Step 3: Apply deterministic rules FIRST
                rule_outcomes = self.rule_engine.apply_rules(world_state, agents, tick, random_gen)
                
                # Step 4: Get LLM decisions for active agents only
                decisions = await self.decision_engine.get_decisions(active_agents, world_state, self.memory_manager)
                
                # Step 5: Update world state atomically
                delta = self.state_manager.apply_actions(world_state, decisions, rule_outcomes)
                
                # Step 6: Update agent memories
                for agent in agents:
                    self.memory_manager.update_working_memory(agent, decisions + rule_outcomes)
                    if agent in active_agents:
                        self.memory_manager.add_episodic_memory(agent, tick, ...)
                await self.memory_manager.compress_if_needed(agents)
                
                # Step 7: Evaluate KPIs
                kpi_values = self.evaluate_kpis(world_state)
                
                # Step 8: Take snapshot
                snapshot = self.state_manager.take_snapshot(world_state, agents)
                
                # Step 9: Log everything
                await self.event_log.save_tick(simulation_run.id, tick, ...)
                
                # Step 10: Broadcast to WebSocket
                await self.broadcast_tick(simulation_run.id, tick, delta, kpi_values)
                
                tick_duration = time.monotonic() - tick_start
    ```

### Verification Checklist

After completing Phase 4, run this test:

- [ ] Create a test scenario with a hardcoded source text (3-4 paragraphs about a policy scenario)
- [ ] Call `world_compiler.compile_world()` → verify it produces a valid WorldModel with entities, factions, KPIs
- [ ] Call `agent_generator.generate_agents()` with count=5 → verify 5 agents created with profiles
- [ ] Run the orchestrator with `max_ticks=3`, `max_active_per_tick=3`
- [ ] Verify: 3 ticks executed, each tick has events logged, KPIs computed, snapshots stored
- [ ] Verify: rule engine runs before decision engine each tick
- [ ] Verify: only 3 agents (not 5) made Gemini calls per tick
- [ ] Verify: memory compression works (add 25 fake episodic memories, verify compression runs)
- [ ] Verify: all random operations use seeded Random (run twice with same seed → same rule outcomes)

**This is the most critical phase. Do not move on until the 5-agent, 3-tick test produces sensible output.**

**STOP after verification. Do not proceed to Phase 5.**
