"""
Tests para utils/rate_limiter.py — BraveRateLimiter.
"""

import asyncio
import time

import pytest
from aifoundry.app.utils.rate_limiter import (
    BraveRateLimiter,
    get_brave_rate_limiter,
    reset_brave_rate_limiter,
)


class TestBraveRateLimiter:
    def test_creation(self):
        limiter = BraveRateLimiter(requests_per_second=2.0, max_retries=5)
        assert limiter.max_retries == 5

    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self):
        """Dos requests seguidas deben esperar el intervalo."""
        limiter = BraveRateLimiter(requests_per_second=10.0)  # 100ms intervalo
        
        times = []
        
        async def record_time():
            times.append(time.monotonic())
            return "ok"
        
        await limiter.execute_with_retry(record_time)
        await limiter.execute_with_retry(record_time)
        
        assert len(times) == 2
        # El intervalo debería ser al menos ~0.1s (100ms)
        elapsed = times[1] - times[0]
        assert elapsed >= 0.05  # Relajado para CI

    @pytest.mark.asyncio
    async def test_retry_on_429(self):
        """Debe reintentar con backoff en errores 429."""
        limiter = BraveRateLimiter(requests_per_second=100.0, max_retries=3)
        call_count = 0
        
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("429 Too Many Requests")
            return "success"
        
        result = await limiter.execute_with_retry(fail_then_succeed)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_other_errors(self):
        """No debe reintentar errores que no son 429."""
        limiter = BraveRateLimiter(requests_per_second=100.0, max_retries=3)
        
        async def fail_with_500():
            raise ValueError("Internal Server Error")
        
        with pytest.raises(ValueError, match="Internal Server Error"):
            await limiter.execute_with_retry(fail_with_500)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Debe fallar después de agotar reintentos."""
        limiter = BraveRateLimiter(requests_per_second=100.0, max_retries=2)
        
        async def always_429():
            raise Exception("429 rate limit exceeded")
        
        with pytest.raises(Exception, match="429"):
            await limiter.execute_with_retry(always_429)

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        limiter = BraveRateLimiter()
        async with limiter:
            pass  # Should not raise


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        reset_brave_rate_limiter()
        a = get_brave_rate_limiter()
        b = get_brave_rate_limiter()
        assert a is b

    def test_reset_creates_new_instance(self):
        a = get_brave_rate_limiter()
        reset_brave_rate_limiter()
        b = get_brave_rate_limiter()
        assert a is not b