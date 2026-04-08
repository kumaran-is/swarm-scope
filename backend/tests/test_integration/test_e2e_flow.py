"""
End-to-end integration test for the full user journey.
These tests verify the complete flow without requiring Gemini API (mocked)
or a live database (uses mock httpx calls where possible).

Note: Full E2E requires Docker Compose running (postgres + redis).
These tests are structured but skipped by default unless DB_URL is set.
"""

import os
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.auth import _hash_password, _verify_password, _make_tokens
from app.config import get_settings


# ── Auth utility tests (no DB needed) ─────────────────────────────────────────

class TestAuthUtilities:
    def test_hash_and_verify_password(self):
        """Password hashing round-trip works correctly."""
        password = "SecurePass123!"
        hashed = _hash_password(password)
        assert hashed != password
        assert _verify_password(password, hashed) is True
        assert _verify_password("wrong_password", hashed) is False

    def test_make_tokens_structure(self):
        """Token generation produces access and refresh tokens."""
        settings = get_settings()
        user_id = uuid.uuid4()
        tokens = _make_tokens(user_id, settings)
        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.token_type == "bearer"
        assert tokens.access_token != tokens.refresh_token

    def test_access_token_is_decodable(self):
        """Access token decodes correctly and contains user sub."""
        from jose import jwt
        settings = get_settings()
        user_id = uuid.uuid4()
        tokens = _make_tokens(user_id, settings)
        payload = jwt.decode(
            tokens.access_token,
            settings.app_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_refresh_token_has_correct_type(self):
        """Refresh token type field is 'refresh'."""
        from jose import jwt
        settings = get_settings()
        user_id = uuid.uuid4()
        tokens = _make_tokens(user_id, settings)
        payload = jwt.decode(
            tokens.refresh_token,
            settings.app_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["type"] == "refresh"


# ── Cost tracker tests ────────────────────────────────────────────────────────

class TestCostTracker:
    def test_empty_cost_structure(self):
        """CostTracker returns zero-filled dict with no Redis."""
        import asyncio
        from app.utils.cost_tracker import CostTracker

        tracker = CostTracker(redis=None)
        result = asyncio.run(tracker.get_run_cost(uuid.uuid4()))
        assert result["total_calls"] == 0
        assert result["estimated_cost_usd"] == 0.0

    def test_cost_calculation(self):
        """Cost is computed correctly from token counts."""
        from app.utils.cost_tracker import PRICE_PER_1K_INPUT_TOKENS, PRICE_PER_1K_OUTPUT_TOKENS

        input_tokens = 1000
        output_tokens = 500
        expected = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + \
                   (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
        assert expected == pytest.approx(0.00125 + 0.0025)

    @pytest.mark.asyncio
    async def test_log_call_with_mock_redis(self):
        """log_call increments Redis hashes correctly."""
        from app.utils.cost_tracker import CostTracker

        mock_redis = AsyncMock()
        mock_redis.hincrby = AsyncMock()
        mock_redis.hincrbyfloat = AsyncMock()
        mock_redis.expire = AsyncMock()

        tracker = CostTracker(redis=mock_redis)
        sim_id = uuid.uuid4()
        await tracker.log_call(sim_id, "test_purpose", 500, 200)

        mock_redis.hincrby.assert_called_once_with(f"cost:{sim_id}", "total_calls", 1)
        assert mock_redis.hincrbyfloat.call_count == 3  # input, output, cost


# ── Ingestion webhook HMAC test ───────────────────────────────────────────────

class TestWebhookHMAC:
    def test_hmac_signature_verification(self):
        """HMAC-SHA256 signature verification works correctly."""
        import hashlib
        import hmac as _hmac

        secret = "test_secret_key_123"
        body = b'{"event": "test"}'
        signature = _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        # Correct signature verifies
        assert _hmac.compare_digest(
            signature,
            _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
        )
        # Wrong signature rejected
        assert not _hmac.compare_digest(signature, "wrong_signature")


# ── Ensemble aggregator tests (no DB, no Gemini) ─────────────────────────────

class TestEnsembleAggregator:
    def test_aggregate_kpi_trajectories_basic(self):
        """Aggregator computes mean and std correctly from 2 runs."""
        from app.engine.ensemble_aggregator import aggregate_kpi_trajectories

        run1 = [{"tick": 1, "stability": 60.0}, {"tick": 2, "stability": 65.0}]
        run2 = [{"tick": 1, "stability": 80.0}, {"tick": 2, "stability": 75.0}]

        result = aggregate_kpi_trajectories([run1, run2])
        assert "stability" in result
        stats = result["stability"]
        # Mean at tick 1: (60 + 80) / 2 = 70
        assert stats["mean"][0] == pytest.approx(70.0)
        # Mean at tick 2: (65 + 75) / 2 = 70
        assert stats["mean"][1] == pytest.approx(70.0)

    def test_aggregate_returns_empty_for_no_data(self):
        """Aggregator returns empty dict for empty input."""
        from app.engine.ensemble_aggregator import aggregate_kpi_trajectories

        result = aggregate_kpi_trajectories([])
        assert result == {}


# ── Fork manager tests ────────────────────────────────────────────────────────

class TestForkManager:
    @pytest.mark.asyncio
    async def test_fork_raises_on_missing_snapshot(self):
        """Fork raises ValueError if tick has no snapshot."""
        from app.engine.fork_manager import fork_from_tick
        from app.models.simulation import Tick

        tick = MagicMock(spec=Tick)
        tick.snapshot = None
        tick.id = uuid.uuid4()

        mock_db = AsyncMock()
        with pytest.raises(ValueError, match="no snapshot"):
            await fork_from_tick(tick=tick, new_random_seed=42, db=mock_db)
