"""Reliability & fault tolerance — retry with exponential backoff (§2.1) and a circuit breaker (§2.2)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class TransientLLMError(Exception):
    """Retryable: transient LLM/tool failures (timeouts, 429/5xx)."""


class CircuitOpenError(Exception):
    """Raised when the circuit is open — fail fast instead of exhausting the pool (§2.2)."""


def llm_retry(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap an LLM/tool coroutine with bounded exponential-backoff retry (§2.1).

    Mirrors the standard: stop after 3 attempts, wait 2..10s exponential, retry only transient errors.
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TransientLLMError, TimeoutError)),
        reraise=True,
    )(fn)


class CircuitBreaker:
    """Minimal circuit breaker (§2.2). Opens after `threshold` consecutive failures; while open it
    fails fast for `reset_timeout` seconds, then allows a single half-open trial. On a clean call it
    closes again. Prevents cascading failures across agent swarms when a downstream LLM degrades."""

    def __init__(self, threshold: int = 5, reset_timeout: float = 30.0) -> None:
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if (time.monotonic() - self._opened_at) >= self.reset_timeout:
            return "half-open"
        return "open"

    def allow(self) -> bool:
        return self.state != "open"

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold and self._opened_at is None:
            self._opened_at = time.monotonic()

    async def call(
        self,
        primary: Callable[..., Any],
        fallback: Callable[..., Any] | None = None,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """Run `primary`; if the circuit is open or `primary` fails, use `fallback` (e.g. a secondary,
        highly-available model) rather than exhausting connection pools."""
        if not self.allow():
            if fallback is not None:
                return await fallback(*args, **kw)
            raise CircuitOpenError("circuit open; no fallback configured")
        try:
            result = await primary(*args, **kw)
        except Exception:
            self.record_failure()
            if fallback is not None:
                return await fallback(*args, **kw)
            raise
        self.record_success()
        return result
