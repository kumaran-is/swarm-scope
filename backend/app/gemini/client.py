"""
GeminiClient — wrapper around google-genai SDK with rate limiting and retry logic.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CallRecord:
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    purpose: str
    simulation_run_id: str | None = None


class GeminiRateLimiter:
    """Tracks and enforces Gemini rate limits and budget caps."""

    def __init__(
        self,
        max_tokens_per_minute: int = 1_000_000,
        max_requests_per_minute: int = 60,
        budget_per_run_usd: float = 5.00,
    ) -> None:
        self.max_tokens_per_minute = max_tokens_per_minute
        self.max_requests_per_minute = max_requests_per_minute
        self.budget_per_run_usd = budget_per_run_usd

        self._window_start = time.monotonic()
        self._tokens_this_window: int = 0
        self._requests_this_window: int = 0
        self._total_cost_usd: float = 0.0
        self._call_log: list[CallRecord] = []

    def _reset_window_if_needed(self) -> None:
        now = time.monotonic()
        if now - self._window_start >= 60:
            self._window_start = now
            self._tokens_this_window = 0
            self._requests_this_window = 0

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """Wait if we're approaching rate limits. Raise if budget is exhausted."""
        self._reset_window_if_needed()

        if self._total_cost_usd >= self.budget_per_run_usd:
            raise RuntimeError(
                f"Gemini budget cap reached: ${self._total_cost_usd:.4f} >= "
                f"${self.budget_per_run_usd:.2f} limit. "
                "Increase gemini_budget_per_run_usd in config or .env to continue."
            )

        while (
            self._tokens_this_window + estimated_tokens > self.max_tokens_per_minute
            or self._requests_this_window >= self.max_requests_per_minute
        ):
            logger.warning(
                "Rate limit approach — waiting 5s (tokens=%d, requests=%d)",
                self._tokens_this_window,
                self._requests_this_window,
            )
            await asyncio.sleep(5)
            self._reset_window_if_needed()

    def record(self, record: CallRecord) -> None:
        self._tokens_this_window += record.tokens_in + record.tokens_out
        self._requests_this_window += 1
        # Rough cost estimate: $0.00001 per token
        self._total_cost_usd += (record.tokens_in + record.tokens_out) * 0.00001
        self._call_log.append(record)
        logger.info(
            "Gemini call recorded: model=%s purpose=%s tokens_in=%d tokens_out=%d latency_ms=%d cost_total=%.4f",
            record.model,
            record.purpose,
            record.tokens_in,
            record.tokens_out,
            record.latency_ms,
            self._total_cost_usd,
        )

    def budget_remaining(self) -> float:
        return max(0.0, self.budget_per_run_usd - self._total_cost_usd)

    def call_stats(self) -> dict[str, Any]:
        return {
            "total_calls": len(self._call_log),
            "total_tokens": sum(r.tokens_in + r.tokens_out for r in self._call_log),
            "total_cost_usd": round(self._total_cost_usd, 4),
            "budget_remaining_usd": round(self.budget_remaining(), 4),
        }


class GeminiClient:
    """
    Wrapper around google-genai SDK.
    Provides structured output, function calling, and embedding modes
    with automatic retry (3x exponential backoff) and rate limiting.
    """

    def __init__(self, rate_limiter: GeminiRateLimiter | None = None) -> None:
        settings = get_settings()
        # Use v1beta endpoint — required for preview models; also avoids regional quota issues
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options={"api_version": "v1beta"},
        )
        self._model = settings.gemini_model
        self._embedding_model = settings.gemini_embedding_model
        self.rate_limiter = rate_limiter or GeminiRateLimiter(
            max_tokens_per_minute=settings.gemini_max_tokens_per_minute,
            max_requests_per_minute=settings.gemini_max_requests_per_minute,
            budget_per_run_usd=settings.gemini_budget_per_run_usd,
        )

    async def _call_with_retry(self, fn, *args, purpose: str = "unknown", **kwargs) -> Any:
        """Execute an SDK call with 3-attempt exponential backoff."""
        delays = [1.0, 2.0, 4.0]
        last_error: Exception | None = None

        for attempt, delay in enumerate(delays, start=1):
            try:
                await self.rate_limiter.acquire()
                start = time.monotonic()
                result = await asyncio.to_thread(fn, *args, **kwargs)
                latency_ms = int((time.monotonic() - start) * 1000)

                # Extract token counts if available
                tokens_in = tokens_out = 0
                if hasattr(result, "usage_metadata"):
                    meta = result.usage_metadata
                    tokens_in = getattr(meta, "prompt_token_count", 0) or 0
                    tokens_out = getattr(meta, "candidates_token_count", 0) or 0

                self.rate_limiter.record(
                    CallRecord(
                        model=self._model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        latency_ms=latency_ms,
                        purpose=purpose,
                    )
                )
                return result

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini call failed (attempt %d/3, purpose=%s): %s",
                    attempt,
                    purpose,
                    exc,
                )
                if attempt < len(delays):
                    jitter = 0.1 * delay
                    await asyncio.sleep(delay + jitter)

        raise RuntimeError(
            f"Gemini call failed after 3 attempts (purpose={purpose})"
        ) from last_error

    async def extract_structured(
        self,
        prompt: str,
        response_schema: type,
        system_prompt: str | None = None,
        purpose: str = "extraction",
    ) -> Any:
        """
        Structured output mode — returns a Pydantic model instance.
        Uses response_mime_type=application/json with a Pydantic schema.
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        if system_prompt:
            config.system_instruction = system_prompt

        contents = [prompt]
        result = await self._call_with_retry(
            self._client.models.generate_content,
            model=self._model,
            contents=contents,
            config=config,
            purpose=purpose,
        )
        return result

    async def call_with_functions(
        self,
        prompt: str,
        function_declarations: list,
        system_prompt: str | None = None,
        purpose: str = "function_call",
    ) -> Any:
        """
        Function calling mode — returns the raw response (caller handles function call parsing).
        """
        tools = [types.Tool(function_declarations=function_declarations)]
        config = types.GenerateContentConfig(tools=tools)
        if system_prompt:
            config.system_instruction = system_prompt

        result = await self._call_with_retry(
            self._client.models.generate_content,
            model=self._model,
            contents=[prompt],
            config=config,
            purpose=purpose,
        )
        return result

    async def generate_embedding(self, text: str, purpose: str = "embedding") -> list[float]:
        """Embedding mode — returns a list of floats."""
        start = time.monotonic()
        result = await asyncio.to_thread(
            self._client.models.embed_content,
            model=self._embedding_model,
            contents=text,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        self.rate_limiter.record(
            CallRecord(
                model=self._embedding_model,
                tokens_in=0,
                tokens_out=0,
                latency_ms=latency_ms,
                purpose=purpose,
            )
        )
        # google-genai SDK returns embeddings in result.embeddings[0].values
        if hasattr(result, "embeddings") and result.embeddings:
            values = result.embeddings[0].values or []
            return [float(v) for v in values]
        raise RuntimeError("No embedding returned from Gemini API")
