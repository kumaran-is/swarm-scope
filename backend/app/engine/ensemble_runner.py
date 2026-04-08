"""
Ensemble runner: orchestrate N parallel simulation runs with different seeds.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.engine.orchestrator import SimulationOrchestrator
from app.gemini.client import GeminiClient
from app.models.ensemble import EnsembleRun
from app.models.simulation import SimulationRun

logger = logging.getLogger(__name__)


class EnsembleRunner:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        client: GeminiClient | None = None,
        max_concurrent_runs: int = 3,
    ) -> None:
        self.session_factory = session_factory
        self.client = client
        self.max_concurrent_runs = max_concurrent_runs

    async def run_ensemble(
        self,
        ensemble_run: EnsembleRun,
        base_random_seed: int = 42,
    ) -> list[SimulationRun]:
        """
        Launch ensemble_size simulation runs with different random seeds.
        Runs up to max_concurrent_runs in parallel.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_runs)
        seeds = [base_random_seed + i for i in range(ensemble_run.ensemble_size)]
        simulation_runs: list[SimulationRun] = []

        # Create SimulationRun records
        async with self.session_factory() as db:
            for idx, seed in enumerate(seeds):
                run = SimulationRun(
                    scenario_id=ensemble_run.scenario_id,
                    random_seed=seed,
                    status="pending",
                    current_tick=0,
                    max_ticks=ensemble_run.base_config.get("max_ticks", 15),
                    config={**ensemble_run.base_config, "ensemble_seed_index": idx},
                    ensemble_run_id=ensemble_run.id,
                    ensemble_seed_index=idx,
                )
                db.add(run)
            await db.commit()

        async def run_one(simulation_run: SimulationRun) -> None:
            async with semaphore:
                async with self.session_factory() as db:
                    orch = SimulationOrchestrator(db=db, client=self.client)
                    await orch.run_simulation(simulation_run)

        tasks = [run_one(run) for run in simulation_runs]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Update ensemble status
        async with self.session_factory() as db:
            ensemble_run.status = "completed"
            await db.commit()

        logger.info(
            "Ensemble %s complete: %d runs with seeds %s",
            ensemble_run.id,
            len(simulation_runs),
            seeds,
        )
        return simulation_runs
