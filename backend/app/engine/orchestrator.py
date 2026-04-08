"""
SimulationOrchestrator — the main tick loop.

10-step tick execution order:
1. Check interventions → apply pending
2. Selective activation → score and pick top K agents
3. Rule resolution → deterministic rules BEFORE LLM
4. Decision engine → Gemini function calling for activated agents
5. State update → apply actions atomically
6. Memory compression → working + episodic + semantic
7. KPI evaluation → compute all KPIs
8. Snapshot → serialize full world state
9. Event log → append immutable event records
10. Broadcast → push tick summary to WebSocket subscribers
"""

import asyncio
import logging
import random
import time
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import (
    activation,
    decision_engine,
    event_log,
    influence_tracker,
    intervention_handler,
    memory_manager,
    rule_engine,
    state_manager,
)
from app.gemini.client import GeminiClient
from app.models.agent import Agent
from app.models.simulation import SimulationRun
from app.models.world import WorldModel

logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    def __init__(
        self,
        db: AsyncSession,
        client: GeminiClient | None = None,
        max_active_per_tick: int = 15,
        broadcast_fn=None,
    ) -> None:
        self.db = db
        self.client = client or GeminiClient()
        self.max_active_per_tick = max_active_per_tick
        self.broadcast_fn = broadcast_fn  # callable(simulation_id, message) or None
        self._pause_flags: dict[str, bool] = {}
        self._stop_flags: dict[str, bool] = {}

    def pause(self, simulation_run_id: str) -> None:
        self._pause_flags[simulation_run_id] = True

    def resume(self, simulation_run_id: str) -> None:
        self._pause_flags[simulation_run_id] = False

    def stop(self, simulation_run_id: str) -> None:
        self._stop_flags[simulation_run_id] = True

    async def _check_pause_or_stop(self, simulation_run_id: str) -> str:
        """Returns 'stop', 'pause', or 'continue'."""
        run_id = str(simulation_run_id)

        if self._stop_flags.get(run_id):
            return "stop"

        # Poll pause state with short waits
        while self._pause_flags.get(run_id):
            logger.info("Simulation %s paused — waiting", run_id)
            await asyncio.sleep(2)
            if self._stop_flags.get(run_id):
                return "stop"

        return "continue"

    async def run_simulation(self, simulation_run: SimulationRun) -> None:
        """
        Execute the full tick loop for a simulation run.
        """
        run_id = str(simulation_run.id)
        logger.info(
            "Starting simulation %s (seed=%d, max_ticks=%d)",
            run_id,
            simulation_run.random_seed,
            simulation_run.max_ticks,
        )

        # Load world state
        world_model = await self._load_world_model(simulation_run.scenario_id)
        agents = await self._load_agents(simulation_run.scenario_id)

        if not world_model or not agents:
            logger.error("Cannot run simulation %s — missing world model or agents", run_id)
            await self._update_run_status(simulation_run, "failed")
            return

        # Initialize world state dict from ORM model
        world_state: dict[str, Any] = {
            "summary": world_model.summary,
            "entities": world_model.entities,
            "factions": world_model.factions,
            "resources": world_model.resources,
            "constraints": world_model.constraints,
            "tensions": world_model.tensions,
            "kpis": world_model.kpis,
            "kpi_values": {
                kpi.get("name", ""): float(kpi.get("initial_value", 50))
                for kpi in world_model.kpis
                if isinstance(kpi, dict)
            },
            "recent_events": [],
            "conflicts": {},
            "alerts": [],
            "scheduled_events": [],
        }

        random_gen = random.Random(simulation_run.random_seed)
        last_activated: dict[str, int] = {}
        total_gemini_calls = 0

        # Mark run as running
        simulation_run.status = "running"
        from datetime import datetime
        simulation_run.started_at = datetime.now(tz=UTC)
        await self.db.commit()

        for tick_num in range(1, simulation_run.max_ticks + 1):
            state = await self._check_pause_or_stop(run_id)
            if state == "stop":
                logger.info("Simulation %s stopped at tick %d", run_id, tick_num)
                break

            tick_start = time.monotonic()
            tick_events: list[dict[str, Any]] = []
            tick_gemini_calls = 0

            # ─── Step 1: Apply pending interventions ───────────────────────
            pending = await intervention_handler.get_pending_interventions(
                simulation_run.id, tick_num, self.db
            )
            interventions_applied_ids: list[str] = []
            for iv in pending:
                result = await intervention_handler.apply_intervention(
                    iv, world_state, agents, self.db, tick_num
                )
                if result.success:
                    interventions_applied_ids.append(result.intervention_id)
                    tick_events.append(
                        event_log.make_event("intervention_applied", None, result.effects, tick_num)
                    )

            # ─── Step 2: Selective activation ──────────────────────────────
            scored = activation.compute_activation_scores(
                agents, world_state, tick_num, last_activated, random_gen
            )
            active_agents = [a for a, _score in scored[: self.max_active_per_tick]]

            for a, _ in scored[: self.max_active_per_tick]:
                last_activated[str(a.id)] = tick_num

            # ─── Step 3: Deterministic rule resolution ─────────────────────
            rule_outcomes = rule_engine.apply_rules(
                world_state, agents, tick_num, random_gen
            )
            for ro in rule_outcomes:
                tick_events.append(
                    event_log.make_event(
                        "rule_outcome", ro.agent_id, {"description": ro.description, "effects": ro.effects}, tick_num
                    )
                )

            # ─── Step 4: LLM decisions for activated agents ────────────────
            decisions = await decision_engine.get_decisions(
                active_agents, world_state, tick_num, client=self.client
            )
            tick_gemini_calls += len(active_agents)
            for d in decisions:
                tick_events.append(
                    event_log.make_event(
                        "agent_action",
                        d.agent_id,
                        {"action": d.action, "params": d.params, "reasoning": d.reasoning},
                        tick_num,
                    )
                )

            # ─── Step 5: Update world state ────────────────────────────────
            delta = state_manager.apply_actions(
                world_state, agents, decisions, rule_outcomes, tick_num
            )

            # ─── Step 6: Memory update ─────────────────────────────────────
            for agent in agents:
                memory_manager.update_working_memory(agent, decisions + rule_outcomes, tick_num)
                if agent in active_agents:
                    memory_manager.add_episodic_memory(
                        agent,
                        tick_num,
                        f"Tick {tick_num}: performed {next((d.action for d in decisions if d.agent_id == str(agent.id)), 'idle')}",
                        emotional_valence=0.0,
                        importance_score=0.5,
                    )

            await memory_manager.compress_if_needed(agents, client=self.client)

            # ─── Step 7: KPI evaluation (already done in apply_actions) ───
            kpi_values = world_state.get("kpi_values", {})

            # ─── Step 8: Snapshot ──────────────────────────────────────────
            snapshot = state_manager.take_snapshot(world_state, agents)

            # ─── Step 9: Log tick to DB ────────────────────────────────────
            await event_log.save_tick(
                simulation_run_id=simulation_run.id,
                tick_number=tick_num,
                phase="complete",
                active_agent_ids=[str(a.id) for a in active_agents],
                events=tick_events,
                world_state_delta=delta.__dict__,
                kpi_values=kpi_values,
                snapshot=snapshot,
                interventions_applied=interventions_applied_ids,
                duration_ms=int((time.monotonic() - tick_start) * 1000),
                gemini_calls=tick_gemini_calls,
                gemini_tokens_used=0,  # populated from rate limiter in production
                db=self.db,
            )

            # Track influence edges
            await influence_tracker.record_influence_edges(
                simulation_run.id, tick_num, decisions, delta, self.db
            )

            # Update run current_tick
            simulation_run.current_tick = tick_num
            await self.db.commit()

            # ─── Step 10: Broadcast ────────────────────────────────────────
            if self.broadcast_fn:
                await self.broadcast_fn(
                    run_id,
                    {
                        "type": "tick_complete",
                        "tick": tick_num,
                        "data": {
                            "kpi_values": kpi_values,
                            "active_agent_count": len(active_agents),
                            "event_count": len(tick_events),
                            "duration_ms": int((time.monotonic() - tick_start) * 1000),
                        },
                    },
                )

            total_gemini_calls += tick_gemini_calls
            logger.info(
                "Tick %d/%d complete: %d active agents, %d events, %dms",
                tick_num,
                simulation_run.max_ticks,
                len(active_agents),
                len(tick_events),
                int((time.monotonic() - tick_start) * 1000),
            )

        # Finalize
        from datetime import datetime
        simulation_run.status = "completed"
        simulation_run.completed_at = datetime.now(tz=UTC)
        await self.db.commit()

        if self.broadcast_fn:
            await self.broadcast_fn(run_id, {"type": "simulation_complete", "tick": simulation_run.current_tick})

        logger.info(
            "Simulation %s complete: %d ticks, %d total gemini calls",
            run_id,
            simulation_run.current_tick,
            total_gemini_calls,
        )

    async def _load_world_model(self, scenario_id: UUID) -> WorldModel | None:
        result = await self.db.execute(
            select(WorldModel).where(WorldModel.scenario_id == scenario_id)
        )
        return result.scalars().first()

    async def _load_agents(self, scenario_id: UUID) -> list[Agent]:
        result = await self.db.execute(
            select(Agent).where(Agent.scenario_id == scenario_id)
        )
        return list(result.scalars().all())

    async def _update_run_status(self, simulation_run: SimulationRun, status: str) -> None:
        simulation_run.status = status
        await self.db.commit()
