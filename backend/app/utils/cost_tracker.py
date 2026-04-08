"""
Cost tracking utility — logs Gemini API call costs to Redis.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# Gemini 2.5 Pro pricing (USD per 1K tokens)
PRICE_PER_1K_INPUT_TOKENS = 0.00125
PRICE_PER_1K_OUTPUT_TOKENS = 0.005


class CostTracker:
    """Track Gemini API costs per simulation run using Redis hashes."""

    def __init__(self, redis=None) -> None:
        self._redis = redis

    async def log_call(
        self,
        simulation_run_id: UUID | str | None,
        purpose: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Increment cost counters for a simulation run in Redis."""
        if not simulation_run_id or not self._redis:
            return
        key = f"cost:{simulation_run_id}"
        try:
            await self._redis.hincrby(key, "total_calls", 1)
            await self._redis.hincrbyfloat(key, "total_input_tokens", input_tokens)
            await self._redis.hincrbyfloat(key, "total_output_tokens", output_tokens)
            cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + \
                   (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
            await self._redis.hincrbyfloat(key, "estimated_cost_usd", cost)
            await self._redis.expire(key, 86400 * 7)  # 7 days TTL
        except Exception as exc:
            logger.warning("Cost tracking failed for %s: %s", simulation_run_id, exc)

    async def get_run_cost(self, simulation_run_id: UUID | str) -> dict:
        """Return cost breakdown for a simulation run."""
        if not self._redis:
            return _empty_cost()
        key = f"cost:{simulation_run_id}"
        try:
            data = await self._redis.hgetall(key)
            if not data:
                return _empty_cost()
            return {
                "total_calls": int(data.get("total_calls", 0)),
                "total_input_tokens": int(float(data.get("total_input_tokens", 0))),
                "total_output_tokens": int(float(data.get("total_output_tokens", 0))),
                "estimated_cost_usd": round(float(data.get("estimated_cost_usd", 0)), 6),
            }
        except Exception as exc:
            logger.warning("Failed to read cost for %s: %s", simulation_run_id, exc)
            return _empty_cost()

    async def get_ensemble_cost(self, ensemble_run_id: UUID | str, run_ids: list[str]) -> dict:
        """Sum cost across all child simulation runs."""
        total = _empty_cost()
        for run_id in run_ids:
            run_cost = await self.get_run_cost(run_id)
            total["total_calls"] += run_cost["total_calls"]
            total["total_input_tokens"] += run_cost["total_input_tokens"]
            total["total_output_tokens"] += run_cost["total_output_tokens"]
            total["estimated_cost_usd"] += run_cost["estimated_cost_usd"]
        total["estimated_cost_usd"] = round(total["estimated_cost_usd"], 6)
        total["ensemble_run_id"] = str(ensemble_run_id)
        total["run_count"] = len(run_ids)
        return total


def _empty_cost() -> dict:
    return {
        "total_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "estimated_cost_usd": 0.0,
    }
