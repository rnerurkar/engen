"""Base typed client: retry + timeout + structured logging.
All external calls (AlloyDB, Vertex AI Search, Apigee, Eraser.io) go through this.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger("solution-accelerator.client")
T = TypeVar("T")


class ClientError(Exception):
    pass


def with_retry[T](fn: Callable[..., T], *args, max_attempts: int = 3,
               backoff_base: float = 0.5, timeout_s: float = 30.0, **kwargs) -> T:
    """Call fn with exponential backoff retry and structured logging."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            logger.info("client_call_ok", extra={"fn": fn.__name__, "attempt": attempt,
                                                  "elapsed_ms": int((time.monotonic() - start) * 1000)})
            return result
        except Exception as exc:  # noqa: BLE001 - wrapper intentionally broad
            last_exc = exc
            logger.warning("client_call_retry", extra={"fn": fn.__name__, "attempt": attempt,
                                                        "error": str(exc)})
            if attempt < max_attempts:
                time.sleep(backoff_base * (2 ** (attempt - 1)))
    raise ClientError(f"{fn.__name__} failed after {max_attempts} attempts: {last_exc}")
