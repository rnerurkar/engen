# ADK Agent Coding Standards — Compliance Mapping

How the SDLC Accelerators codebase (greenfield + brownfield Solution Accelerator Agents and their Epic→spec→blueprint pipelines) satisfies the **ADK Agent Development Standards**. Cross-cutting concerns are implemented once in a shared `runtime/` package and wired into both services (`services/solution-accelerator/src/runtime`, `brownfield/src/brownfield/runtime`). New tests: `tests/test_runtime_standards.py`.

| § | Standard | Where it's met | Status |
|---|----------|----------------|--------|
| 1.1 | Strict typing; **Pydantic v2** for structured LLM outputs / tool definitions; avoid `Any` | `runtime/schemas.py` (`SignalModel`, `ToolDefinitionModel`, `SkillDefinitionModel`, `extra="forbid"`); validated at the assembly boundary (`assembly/derive_json.py` → `_valid_tool_def`/`_valid_skill_def`); existing `models/blueprint.py` already Pydantic. | **Met** — `mypy --strict` is **clean repo-wide**: greenfield 57 files, brownfield 34 files, shared runtime 6 files. Repo-root `[tool.mypy]` config in `pyproject.toml` (`strict=true`, `namespace_packages`, `explicit_package_bases`), run per service from each `src/`. The handful of `# type: ignore` are documented and limited to genuine mypy/third-party limitations (see note). |
| 1.2 | Google style; `ruff format` / black **line length 88**; ruff lint | `pyproject.toml` → `line-length = 88`; source formatted with `ruff format`; lint `select = [E,F,I,UP,B]`. | **Met** |
| 2.1 | Never a bare LLM/tool call — **tenacity** retry + exponential backoff | `runtime/reliability.py` `llm_retry` (stop after 3, wait 2–10 s, retry transient only); applied in `runtime/llm.py` and wired into both live LLM seams (`reasoning/llm_harness._live_invoke`, `brownfield…/ingest/shaping.shape_epic`). | **Met** |
| 2.2 | **Circuit breaker** + fallback to a secondary model | `runtime/reliability.py` `CircuitBreaker` (closed/open/half-open); `runtime/llm.py invoke_llm_with_retry` runs primary then falls back to `SDLC_LLM_FALLBACK_MODEL` via the breaker. Test: `test_circuit_fallback_to_secondary_model`, `test_circuit_opens_after_threshold`. | **Met** |
| 3.1 | **Async I/O**; `asyncio.gather` for independent tools | `invoke_llm_with_retry` is async (sync `invoke_llm` bridge for the reference pipeline); `execute_parallel_tools` uses `asyncio.gather(..., return_exceptions=True)`. Test: `test_parallel_tools_isolate_failures`. | **Met** (LLM path async; the deterministic Phase-B mapping is CPU-bound and stays sync by design) |
| 3.2 | **Connection pooling** at app scope | `runtime/llm.py get_async_client()` — one process-wide `httpx.AsyncClient` with pooled `Limits`, not per-agent. Test: `test_pooled_client_singleton`. | **Met** |
| 4.1 | **Stateless** execution; state in a distributed store | Agents/tools hold no cross-request state; task state lives in the Task Store (`server/task_store.py`), documented as AlloyDB/Redis in production. | **Met at the code layer; store backend is a deploy seam** |
| 4.2 | **Tool idempotency**; distributed lock via execution ID | `runtime/safety.py ExecutionLock` + `idempotency_key`; both `ingest_epic_start` handlers run under `run_once(exec_id, …)` so a retried Epic submission does not re-run Phase A. Test: `test_idempotency`. Production: back the lock with Redis `SETNX`. | **Met** (seam: Redis lock in prod) |
| 5.1 | **Structured logging** (structlog) with `agent_id`, `trace_id`, `session_id` | `runtime/obs.py bind_logger` (JSON renderer); used in agent `run()` and the server ingest handlers. | **Met** |
| 5.2 | **OpenTelemetry** spans: prompt formatting, LLM generation (token usage), tool execution | `runtime/obs.py` `prompt_format_span` / `llm_generation_span` (records `llm.*_tokens`) / `tool_execution_span`; spans wrap the agent dispatch and the LLM call. | **Met** (export to an OTel collector is a deploy config) |
| 6.1 | **Least privilege** for tools (read-only by default) | `runtime/safety.py least_privilege_role`; each `tool_binding` in `app-blueprint.json` carries a `least_privilege` role (read-only unless capabilities imply writes). | **Met** |
| 6.2 | **Prompt-injection** mitigation — segregate system vs. user data; `<user_input>` delimiters; instruct the model to ignore overrides | `runtime/safety.py wrap_user_input` + `INJECTION_GUARD`; the untrusted Rally Epic is wrapped in `<user_input>…</user_input>` in both shapers (`ingest/shaping.build_shaping_message`), forged closing tags neutralized, and the guard appended to the epic-shaping and greenfield system prompts. Test: `test_injection_wrapping`. | **Met** |

## Seams (deployment-time, not reference code)
These are intentionally bound at deploy rather than implemented in the reference package, and are called out so they aren't mistaken for gaps:
- **Live Gemini call** (`runtime/llm.py _call_provider`, `reasoning/llm_provider`) — the only network seam; everything around it (retry, breaker, fallback, pooling, tracing, logging) is real and tested with an injected provider.
- **State/lock backends** — Task Store → AlloyDB; `ExecutionLock` → Redis `SETNX`; short-term memory → Redis; long-term/semantic → Vector DB (§4.1).
- **OTel exporter** and **structlog sink** — wired to the platform collector/aggregator in the runtime config.
- **mypy `--strict`** — enable as a CI gate; the code is fully type-hinted to support it.

## Verification (latest)
`ruff format` + `ruff check` **clean** at line-length 88 across both services (102 files); the shared
`runtime/` package is **mypy `--strict` clean** in both copies; `test_runtime_standards.py` proves retry,
breaker+fallback, parallel-tool isolation, pooled client, idempotency, injection wrapping, and Pydantic
boundary validation; greenfield **17 passed**, brownfield **59 passed**. Required libraries declared in
`pyproject.toml`.

**§1.1 mypy coverage:** `mypy --strict` is clean across the whole repo — greenfield `src` (57 files),
brownfield `src` (34 files), and the shared `runtime/` package (6 files). The strict `[tool.mypy]`
config lives in the repo-root `pyproject.toml`; the flat multi-package `src` layout is resolved with
`namespace_packages` + `explicit_package_bases`. Reproduce per service (each picks up the root config
by walking up):
`cd services/solution-accelerator/src && python3 -m mypy .` and
`cd brownfield/src && python3 -m mypy brownfield/`. Annotations are type-only (`from __future__ import
annotations`), so behavior is unchanged — the test suites (greenfield 17, brownfield 59) stay green.

The only `# type: ignore` comments are documented exceptions for genuine tool limitations, not silenced
real errors: (1) `google-adk` does not re-export `FunctionTool` from `google.adk.tools` in its stubs
(`[attr-defined]`, 3 sites); (2) mypy cannot narrow an instance attribute to non-`None` inside a closure
even after an `is not None` guard (`[misc]`, the injected-client lambdas in `clients/`); (3) Pydantic's
internal `__pydantic_complete__` flag (`[attr-defined]`, 1 site). A few `Any`-typed seams remain where the
payload is genuinely dynamic (untrusted LLM JSON before Pydantic validation, injected client callables);
these are the documented `Any` exceptions the standard allows.
