"""Observability — structured logging (§5.1) and distributed tracing (§5.2)."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Any, cast

import structlog
from opentelemetry import trace

_CONFIGURED = False


def configure_logging() -> None:
    """JSON structured logging so aggregators can parse agent metadata (§5.1)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def bind_logger(
    *, agent_id: str = "", trace_id: str = "", session_id: str = "", **extra: Any
) -> structlog.BoundLogger:
    """Return a logger with agent_id, trace_id, session_id bound into context (§5.1)."""
    configure_logging()
    return cast(
        structlog.BoundLogger,
        structlog.get_logger().bind(
            agent_id=agent_id, trace_id=trace_id, session_id=session_id, **extra
        ),
    )


_tracer = trace.get_tracer("sdlc-accelerators.adk")


@contextlib.contextmanager
def _span(name: str, **attrs: Any) -> Iterator[Any]:
    with _tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            if v is not None:
                span.set_attribute(k, v)
        yield span


def prompt_format_span(**attrs: Any) -> AbstractContextManager[Any]:
    """Span around prompt formatting/templating (§5.2)."""
    return _span("prompt.format", **attrs)


def llm_generation_span(model: str = "", **attrs: Any) -> AbstractContextManager[Any]:
    """Span around LLM generation; record token usage via span attributes (§5.2)."""
    return _span("llm.generation", **{"llm.model": model, **attrs})


def tool_execution_span(tool: str = "", **attrs: Any) -> AbstractContextManager[Any]:
    """Span around tool execution and parsing (§5.2)."""
    return _span("tool.execution", **{"tool.name": tool, **attrs})
