"""Shared ADK runtime — cross-cutting concerns mandated by the ADK Agent Coding Standards.

Reliability (§2): tenacity retry + circuit breaker + model fallback.
Performance (§3): pooled async httpx client + asyncio.gather parallel tool execution.
Observability (§5): structlog structured logging + OpenTelemetry spans (prompt / generation / tool).
Security (§6): prompt-injection delimiters + least-privilege tool roles.
State (§4): idempotent execution via execution-ID distributed lock (seam: Redis in prod).
Typing (§1): Pydantic v2 boundary models (see runtime.schemas).
"""

from .llm import (
    execute_parallel_tools,
    get_async_client,
    invoke_llm,
    invoke_llm_with_retry,
)
from .obs import (
    bind_logger,
    configure_logging,
    llm_generation_span,
    prompt_format_span,
    tool_execution_span,
)
from .reliability import CircuitBreaker, CircuitOpenError, llm_retry
from .safety import (
    INJECTION_GUARD,
    ExecutionLock,
    idempotency_key,
    least_privilege_role,
    wrap_user_input,
)

__all__ = [
    "bind_logger",
    "configure_logging",
    "llm_generation_span",
    "prompt_format_span",
    "tool_execution_span",
    "CircuitBreaker",
    "CircuitOpenError",
    "llm_retry",
    "execute_parallel_tools",
    "get_async_client",
    "invoke_llm",
    "invoke_llm_with_retry",
    "INJECTION_GUARD",
    "ExecutionLock",
    "idempotency_key",
    "least_privilege_role",
    "wrap_user_input",
]
