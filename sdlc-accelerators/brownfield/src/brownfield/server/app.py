"""Brownfield Solution Accelerator MCP Server — async blueprint tools, OAuth 2.1 + Entra protected.

Exposes blueprint_start/status/result over the async MCP Tasks pattern (parallels greenfield).
Every tool is gated by require_auth (JWT validation + Solution Architect group). owner_id (from
JWT sub) enforces task + contract-store tenant isolation. The brownfield pipeline runs server-side;
the design_contract + blueprint + diagram DSLs persist to the DesignContractStore (GCS + AlloyDB
pointer), and blueprint_result reads them back by task_id.

Transport binding (MCP SDK) is the remaining live seam; the handlers + auth + store are real.
"""
from __future__ import annotations

import importlib.util as _ilu
import os
import sys

_HERE = os.path.dirname(__file__)
# Resolve the repo root once and use the centralized cross-service path bootstrap, instead of
# fragile per-file dirname chains. (brownfield/src is added so `brownfield.*` resolves; mcp-auth
# is added so the shared OAuth library resolves.)
_repo_root = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
import _srcpaths  # noqa: E402

_srcpaths.ensure("brownfield", "mcp-auth")

# Load the brownfield task store by path (avoid name clashes with greenfield's).
_ts_spec = _ilu.spec_from_file_location("bf_task_store", os.path.join(_HERE, "task_store.py"))
_ts = _ilu.module_from_spec(_ts_spec)
sys.modules[_ts_spec.name] = _ts
_ts_spec.loader.exec_module(_ts)
TaskStore = _ts.TaskStore

from oauth_config import OAuthConfig  # type: ignore

from brownfield.artifact_store.store import DesignContractStore
from brownfield.map_current_to_target import SubstitutionRow
from brownfield.pipeline import MigrationReadinessBlocked, run_brownfield_pipeline

_store = TaskStore()
_CFG = OAuthConfig.from_env()
_CONTRACT_STORE = DesignContractStore()   # design_contract + blueprint + diagrams -> GCS + AlloyDB pointer

# Injection seams (parallel to greenfield).
_DECODE = None        # JWT decode (live: Entra JWKS)
_GCS_PUT = None       # GCS upload seam
_GCS_GET = None       # GCS download seam
_SUBSTITUTION_ROWS: list = []   # loaded from the decision-table store (authored content)
_ADR_RULES: list = []           # loaded from the ADR Constraint Store (authored content)
_RECOMMEND_FN = None            # inject a recommend fn in tests; else the live LLM provider runs
_USE_ADK_ORCHESTRATOR = False   # opt-in: expose the pipeline as the brownfield_migration_orchestrator
                                # (ADK SequentialAgent). Off by default — the tested pipeline runs
                                # directly. When on + ADK installed, blueprint_start drives the
                                # SequentialAgent whose ONE LlmAgent is brownfield_pattern_recommender;
                                # substitution/ADR/assembly remain deterministic steps.


def _gate(handler):
    def wrapper(*args, authorization_header=None, **kwargs):
        from middleware import authenticate as _auth
        auth = _auth(authorization_header, _CFG, _decode=_DECODE)
        if not auth.ok:
            return {"_auth_error": True, "status": auth.status, "headers": auth.headers, "body": auth.body}
        return handler(*args, principal=auth.principal, **kwargs)
    wrapper.__name__ = getattr(handler, "__name__", "wrapped")
    return wrapper


@_gate
def blueprint_start(spec: str, plan: str, *, principal) -> dict:
    """Start an async brownfield blueprint task. Runs the pipeline server-side, persists the
    design contract + blueprint + diagram DSLs to the store, returns a taskId to poll."""
    task = _store.create(principal.sub)
    try:
        rows = [r if isinstance(r, SubstitutionRow) else SubstitutionRow(**r) for r in _SUBSTITUTION_ROWS]
        result = run_brownfield_pipeline(spec, plan, rows, adr_rules=_ADR_RULES,
                                         recommend_fn=_RECOMMEND_FN)
        _CONTRACT_STORE.write_contract(task.task_id, principal.sub, result["blueprint_md"],
                                       result["design_contract"], result["diagrams"], _gcs_put=_GCS_PUT)
        _store.update(task.task_id, status="completed",
                      result={"artifacts_stored": True, "readiness": result["readiness"]}, stage="done")
    except MigrationReadinessBlocked as e:
        _store.update(task.task_id, status="failed", error=str(e),
                      result={"readiness_block": True, "score": e.report.score}, stage="validate_spec")
    except Exception as e:  # surface pipeline errors (e.g. unresolved substitution) as task failure
        _store.update(task.task_id, status="failed", error=str(e), stage="pipeline")
    return {"taskId": task.task_id, "status": _store.get(task.task_id).status, "pollInterval": 10000}


@_gate
def blueprint_status(taskId: str, *, principal) -> dict:
    t = _store.get(taskId)
    if not t:
        return {"error": "unknown task"}
    if t.owner_id != principal.sub:
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    return {"taskId": taskId, "status": t.status, "stage": t.stage,
            **({"error": t.error} if t.error else {})}


@_gate
def blueprint_result(taskId: str, *, principal) -> dict:
    """Read the design contract + blueprint + diagram DSLs back from the store (GCS via AlloyDB
    pointer), owner_id-isolated, combined for the IDE."""
    t = _store.get(taskId)
    if not t or t.status != "completed":
        return {"error": "not ready", "status": t.status if t else "unknown",
                **({"detail": t.error} if t and t.error else {})}
    if t.owner_id != principal.sub:
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    ptr = _CONTRACT_STORE.read_pointer(taskId)
    if not ptr or ptr.owner_id != principal.sub:
        return {"error": "artifacts not found"}
    return _CONTRACT_STORE.read_contract(taskId, _gcs_get=_GCS_GET)


TOOLS = {
    "blueprint_start": blueprint_start,
    "blueprint_status": blueprint_status,
    "blueprint_result": blueprint_result,
}
