"""Solution Accelerator MCP Server — all tools, OAuth 2.1 + Entra ID protected.

Exposes: blueprint_start/status/result, ingest_epic_start/status/result, assemble_blueprint,
validate_composition, refresh.
Every tool is gated by require_auth (JWT validation + Solution Architect group). owner_id
(from JWT sub) enforces Task Store tenant isolation. On auth failure the handler returns
401/403 + WWW-Authenticate, which drives the IDE back through the Entra OAuth flow.

Transport binding (MCP SDK) is the remaining live seam; the handlers + auth are real.
"""

from __future__ import annotations

import os
import sys
from typing import Any, cast

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(_root, "mcp-auth", "src"))

import importlib.util as _ilu
import os as _os

_ts_spec = _ilu.spec_from_file_location(
    "sa_task_store", _os.path.join(_os.path.dirname(__file__), "task_store.py")
)
assert _ts_spec is not None and _ts_spec.loader is not None
_ts = _ilu.module_from_spec(_ts_spec)
import sys as _sys

_sys.modules[_ts_spec.name] = _ts
_ts_spec.loader.exec_module(_ts)
TaskStore = _ts.TaskStore
from artifact_store.store import BlueprintArtifactStore
from assembly.validate_composition import validate_composition as _validate_composition

# Auth (shared library)
from oauth_config import OAuthConfig
from runtime.safety import ExecutionLock as _ExecutionLock

_INGEST_LOCK: _ExecutionLock | None = None

_store = TaskStore()
_CFG = OAuthConfig.from_env()


# Allow tests to inject a decode fn (live path uses Entra JWKS inside validate_token)
_DECODE = None
_ERASER_MCP = None  # injected Eraser MCP client for diagram rendering (live transport is the seam)
_ARTIFACT_STORE = (
    BlueprintArtifactStore()
)  # blueprint artifacts -> GCS + AlloyDB pointer
_GCS_PUT = None  # injectable GCS upload seam
_GCS_GET = None  # injectable GCS download seam


def _gate(handler: Any) -> Any:
    def wrapper(*args: Any, authorization_header: Any = None, **kwargs: Any) -> Any:
        from middleware import authenticate as _auth

        auth = _auth(authorization_header, _CFG, _decode=_DECODE)
        if not auth.ok:
            return {
                "_auth_error": True,
                "status": auth.status,
                "headers": auth.headers,
                "body": auth.body,
            }
        return handler(*args, principal=auth.principal, **kwargs)

    wrapper.__name__ = getattr(handler, "__name__", "wrapped")
    return wrapper


@_gate
def blueprint_start(spec: str, plan: str, *, principal: Any) -> dict[str, Any]:
    """ASYNC START. owner_id = principal.sub (Task Store tenant isolation).

    The pipeline DELEGATES to the Solution Accelerator Agent (one ADK agent) — Step 5 runs its
    recommend_architecture FunctionTool. The server itself does not reason."""
    task = _store.create(owner_id=principal.sub)
    try:
        _store.update(task.task_id, status="running", stage="pipeline")
        # The reasoning+assembly pipeline runs here (live: Cloud Run Job via Cloud Tasks).
        from pipeline.orchestrator import run_pipeline

        result = run_pipeline(spec, plan, eraser_mcp=_ERASER_MCP)
        # Persist all blueprint artifacts to GCS + AlloyDB pointer (read back by blueprint_result).
        _ARTIFACT_STORE.write_blueprint(
            task.task_id,
            principal.sub,
            result["markdown"],
            result["json"],
            result.get("diagrams", []),
            _gcs_put=_GCS_PUT,
        )
        # Task result holds only lightweight status; artifacts live in the store.
        _store.update(
            task.task_id,
            status="completed",
            result={"artifacts_stored": True},
            stage="done",
        )
    except NotImplementedError as e:
        # Reasoning is wired to the live Gemini provider; this means the live path isn't
        # CONFIGURED in this environment (no credentials). See reasoning/llm_provider.py.
        _store.update(
            task.task_id, status="failed", error=f"reasoning_not_configured: {e}"
        )
    except Exception as e:  # noqa: BLE001
        _store.update(task.task_id, status="failed", error=str(e))
    return {"taskId": task.task_id, "pollInterval": 5, "status": "queued"}


@_gate
def blueprint_status(taskId: str, *, principal: Any) -> dict[str, Any]:
    t = _store.get(taskId)
    if not t:
        return {"status": "failed", "error": "unknown taskId"}
    if t.owner_id != principal.sub:  # tenant isolation
        return {
            "_auth_error": True,
            "status": 403,
            "body": {"error": "forbidden", "error_description": "Not your task"},
        }
    return {"status": t.status, "stage": t.stage, "error": t.error}


@_gate
def blueprint_result(taskId: str, *, principal: Any) -> dict[str, Any] | None:
    """Read all blueprint artifacts back from the store (GCS via AlloyDB pointer) and return
    md + json + diagrams (base64) to the IDE, combined into one response."""
    t = _store.get(taskId)
    if not t or t.status != "completed":
        return {"error": "not ready", "status": t.status if t else "unknown"}
    if t.owner_id != principal.sub:
        return {
            "_auth_error": True,
            "status": 403,
            "body": {"error": "forbidden", "error_description": "Not your task"},
        }
    ptr = _ARTIFACT_STORE.read_pointer(taskId)
    if not ptr or ptr.owner_id != principal.sub:
        return {"error": "artifacts not found"}
    blueprint = _ARTIFACT_STORE.read_blueprint(taskId, _gcs_get=_GCS_GET)
    return blueprint  # {markdown, json, diagrams[], gcs_prefix}


@_gate
def ingest_epic_start(epic: dict[str, Any], *, principal: Any) -> dict[str, Any]:
    """ASYNC START — Greenfield Epic ingestion (optional front door).

    Receives a Rally Epic payload (CONTENT only — no credentials; the coding agent fetched it client-side
    via the Rally MCP server using the developer's Entra ID SSO). Runs the two-phase pipeline:
      Phase A — DELEGATES to the Solution Accelerator Agent (one ADK agent), which runs its
                create_epic_signal_ledger FunctionTool (extractive shaping → Epic Signal Ledger), then
      Phase B — deterministic mapping (ledger → signal-bearing spec.md + fill-ratio confidence + Rally
                provenance stamp).
    owner_id = principal.sub (Task Store tenant isolation). Result holds spec.md + ledger (text/JSON, no
    binaries) so it lives in the task result, not the GCS blueprint artifact store.
    """
    task = _store.create(owner_id=principal.sub)
    from runtime import bind_logger, idempotency_key

    global _INGEST_LOCK
    if _INGEST_LOCK is None:
        _INGEST_LOCK = _ExecutionLock()
    import json as _json

    log = bind_logger(
        agent_id="solution_accelerator_agent",
        session_id=principal.sub,
        trace_id=task.task_id,
    )
    # §4.2 — idempotent start: a retried submission of the same Epic by the same owner reuses the prior
    # task instead of re-running Phase A (seam: a Redis SETNX lock in production).
    exec_id = idempotency_key(
        principal.sub, _json.dumps(epic, sort_keys=True, default=str)
    )

    def _do() -> dict[str, Any]:
        try:
            _store.update(task.task_id, status="running", stage="shaping")
            log.info("ingest.start", taskId=task.task_id, exec_id=exec_id)
            from ingest.orchestrator import run_ingest

            result = run_ingest(
                epic, on_phase=lambda phase: _store.update(task.task_id, stage=phase)
            )
            if result.get("empty"):
                _store.update(
                    task.task_id,
                    status="failed",
                    error="empty_ledger: the Epic has no description/acceptance criteria to "
                    "shape. Flesh out the Rally Epic, or fall back to /specify.",
                )
                log.warning("ingest.empty", taskId=task.task_id)
                return {"taskId": task.task_id, "pollInterval": 5, "status": "queued"}
            _store.update(task.task_id, status="completed", stage="done", result=result)
            log.info("ingest.completed", taskId=task.task_id)
        except NotImplementedError as e:
            _store.update(
                task.task_id, status="failed", error=f"reasoning_not_configured: {e}"
            )
            log.error("ingest.not_configured", taskId=task.task_id, error=str(e))
        except Exception as e:  # noqa: BLE001
            _store.update(task.task_id, status="failed", error=str(e))
            log.error("ingest.failed", taskId=task.task_id, error=str(e))
        return {"taskId": task.task_id, "pollInterval": 5, "status": "queued"}

    return cast("dict[str, Any]", _INGEST_LOCK.run_once(exec_id, _do))


@_gate
def ingest_epic_status(taskId: str, *, principal: Any) -> dict[str, Any]:
    t = _store.get(taskId)
    if not t:
        return {"status": "failed", "error": "unknown taskId"}
    if t.owner_id != principal.sub:  # tenant isolation
        return {
            "_auth_error": True,
            "status": 403,
            "body": {"error": "forbidden", "error_description": "Not your task"},
        }
    return {"status": t.status, "phase": t.stage, "error": t.error}


@_gate
def ingest_epic_result(taskId: str, *, principal: Any) -> dict[str, Any]:
    """RETRIEVE — returns { spec_md, epic_signal_ledger, per_section_confidence, provenance }.
    The prompt file writes spec.md + epic-signal-ledger.json to the workspace."""
    t = _store.get(taskId)
    if not t or t.status != "completed":
        return {
            "error": "not ready",
            "status": t.status if t else "unknown",
            **({"detail": t.error} if t and t.error else {}),
        }
    if t.owner_id != principal.sub:
        return {
            "_auth_error": True,
            "status": 403,
            "body": {"error": "forbidden", "error_description": "Not your task"},
        }
    return cast(
        "dict[str, Any]", t.result
    )  # {spec_md, epic_signal_ledger, per_section_confidence, provenance, empty}


@_gate
def assemble_blueprint_tool(
    selections: dict[str, Any], spec: str, plan: str, *, principal: Any
) -> dict[str, Any]:
    """Deterministic assembly (selections already validated). Builds md+json+DSL and runs the
    two-phase Eraser MCP render (submit DSL, then fetch .drawio.xml + .png). _ERASER_MCP is the
    injected Eraser MCP client (live transport is the seam)."""
    from assembly.assemble import assemble_blueprint
    from assembly.selections import ArchitectureSelections

    result = assemble_blueprint(
        ArchitectureSelections(**selections), spec, plan, eraser_mcp=_ERASER_MCP
    )
    return {
        "markdown": result.markdown,
        "json": result.json,
        "diagrams": result.diagrams,
    }


@_gate
def validate_composition(
    agent_tree: dict[str, Any], *, principal: Any
) -> dict[str, Any]:
    r = _validate_composition(agent_tree)
    return {
        "valid": r.valid,
        "violations": [{"rule": v.rule, "detail": v.detail} for v in r.violations],
    }


@_gate
def refresh(
    blueprint_md: str,
    drawio_files: dict[str, Any],
    spec: str,
    plan: str,
    hashes_path: str,
    last_json: dict[str, Any],
    *,
    principal: Any,
) -> dict[str, Any]:
    from refresh.orchestrator import refresh as _refresh

    res = _refresh(blueprint_md, drawio_files, spec, plan, hashes_path, last_json)
    return {
        "sync_report": res.sync_report.__dict__,
        "structural_report": (
            res.structural_report.__dict__ if res.structural_report else None
        ),
    }


TOOLS = {
    "blueprint_start": blueprint_start,
    "blueprint_status": blueprint_status,
    "blueprint_result": blueprint_result,
    "ingest_epic_start": ingest_epic_start,
    "ingest_epic_status": ingest_epic_status,
    "ingest_epic_result": ingest_epic_result,
    "assemble_blueprint": assemble_blueprint_tool,
    "validate_composition": validate_composition,
    "refresh": refresh,
}


def serve() -> None:  # pragma: no cover - transport wiring
    """TODO(live): bind TOOLS to the MCP SDK transport on Cloud Run; pass the
    Authorization header from each MCP request into the handler as authorization_header."""
    raise NotImplementedError(
        "Bind TOOLS to the MCP SDK transport (Cloud Run) + TLS 1.3."
    )
