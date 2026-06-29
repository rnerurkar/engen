"""LLM invocation — async I/O (§3.1), connection pooling (§3.2), retry + circuit breaker + model
fallback (§2.1, §2.2), wrapped in observability spans (§5.2).

The actual Gemini HTTP request is the single seam (`_call_provider`); everything around it — pooling,
retry, breaker, fallback, tracing, structured logging — is real and tested with an injected provider.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx

from .obs import bind_logger, llm_generation_span
from .reliability import CircuitBreaker, llm_retry

_PRIMARY_MODEL = os.environ.get("SDLC_LLM_MODEL", "gemini-2.5-pro")
_FALLBACK_MODEL = os.environ.get("SDLC_LLM_FALLBACK_MODEL", "gemini-2.0-flash")

# §3.2 — one pooled AsyncClient at module/app scope (NOT per agent). Reuses TLS connections.
_CLIENT: httpx.AsyncClient | None = None
_BREAKER = CircuitBreaker(threshold=5, reset_timeout=30.0)


def get_async_client() -> httpx.AsyncClient:
    """Return the process-wide pooled httpx.AsyncClient (§3.2)."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _CLIENT


async def aclose_client() -> None:
    global _CLIENT
    if _CLIENT is not None:
        await _CLIENT.aclose()
        _CLIENT = None


async def _call_provider(
    system_prompt: str, user_message: str, model: str
) -> dict[str, Any]:
    """LIVE SEAM: the Gemini call over the pooled client. Bound at deploy time. Transient HTTP errors
    (timeout/429/5xx) are re-raised as TransientLLMError so the retry/breaker can act."""
    raise NotImplementedError(
        "Bind the live Gemini call here using get_async_client(); map 429/5xx/timeout to TransientLLMError."
    )


@llm_retry
async def _attempt(
    provider: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    user_message: str,
    model: str,
) -> dict[str, Any]:
    return await provider(system_prompt, user_message, model)


async def invoke_llm_with_retry(
    system_prompt: str,
    user_message: str,
    *,
    model: str | None = None,
    agent_id: str = "",
    trace_id: str = "",
    session_id: str = "",
    provider: Callable[..., Awaitable[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Async LLM call with retry (§2.1), circuit breaker + secondary-model fallback (§2.2), pooled
    client (§3.2), and a generation span carrying token usage (§5.2). `provider` is injectable for tests.
    """
    provider = provider or _call_provider
    model = model or _PRIMARY_MODEL
    log = bind_logger(agent_id=agent_id, trace_id=trace_id, session_id=session_id)

    async def primary() -> dict[str, Any]:
        with llm_generation_span(model=model) as span:
            log.info("llm.invoke", model=model, tier="primary")
            out = cast(
                "dict[str, Any]",
                await _attempt(provider, system_prompt, user_message, model),
            )
            _record_tokens(span, out)
            return out

    async def fallback() -> dict[str, Any]:
        with llm_generation_span(model=_FALLBACK_MODEL, fallback=True) as span:
            log.warning(
                "llm.fallback", model=_FALLBACK_MODEL, reason="primary unavailable/open"
            )
            out = cast(
                "dict[str, Any]",
                await _attempt(provider, system_prompt, user_message, _FALLBACK_MODEL),
            )
            _record_tokens(span, out)
            return out

    return cast("dict[str, Any]", await _BREAKER.call(primary, fallback))


def _record_tokens(span: Any, out: dict[str, Any]) -> None:
    usage = (out or {}).get("usage") or {}
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        if k in usage:
            span.set_attribute(f"llm.{k}", usage[k])


def invoke_llm(system_prompt: str, user_message: str, **kw: Any) -> dict[str, Any]:
    """Sync bridge for the synchronous reference pipeline — runs the async path on a fresh loop."""
    return asyncio.run(invoke_llm_with_retry(system_prompt, user_message, **kw))


async def execute_parallel_tools(
    tool_calls: list[Callable[[], Awaitable[Any]]],
) -> list[Any]:
    """Run independent agent tools concurrently (§3.1). Returns results/exceptions positionally so one
    tool's failure never crashes the batch."""
    return await asyncio.gather(*(c() for c in tool_calls), return_exceptions=True)
