"""Solution Accelerator MCP Server — all tools, OAuth 2.1 + Entra ID protected.

Exposes: blueprint_start/status/result, assemble_blueprint, validate_composition, refresh.
Every tool is gated by require_auth (JWT validation + Solution Architect group). owner_id
(from JWT sub) enforces Task Store tenant isolation. On auth failure the handler returns
401/403 + WWW-Authenticate, which drives the IDE back through the Entra OAuth flow.

Transport binding (MCP SDK) is the remaining live seam; the handlers + auth are real.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(_root, "mcp-auth", "src"))

import importlib.util as _ilu
import os as _os

_ts_spec = _ilu.spec_from_file_location('sa_task_store', _os.path.join(_os.path.dirname(__file__), 'task_store.py'))
_ts = _ilu.module_from_spec(_ts_spec)
import sys as _sys

_sys.modules[_ts_spec.name] = _ts
_ts_spec.loader.exec_module(_ts)
TaskStore = _ts.TaskStore
from artifact_store.store import BlueprintArtifactStore
from assembly.validate_composition import validate_composition as _validate_composition

# Auth (shared library)
from oauth_config import OAuthConfig  # type: ignore

_store = TaskStore()
_CFG = OAuthConfig.from_env()


# Allow tests to inject a decode fn (live path uses Entra JWKS inside validate_token)
_DECODE = None
_ERASER_MCP = None  # injected Eraser MCP client for diagram rendering (live transport is the seam)
_ARTIFACT_STORE = BlueprintArtifactStore()  # blueprint artifacts -> GCS + AlloyDB pointer
_GCS_PUT = None                              # injectable GCS upload seam
_GCS_GET = None                              # injectable GCS download seam


def _gate(handler):
    def wrapper(*args, authorization_header=None, **kwargs):
        from middleware import authenticate as _auth
        auth = _auth(authorization_header, _CFG, _decode=_DECODE)
        if not auth.ok:
            return {'_auth_error': True, 'status': auth.status, 'headers': auth.headers, 'body': auth.body}
        return handler(*args, principal=auth.principal, **kwargs)
    wrapper.__name__ = getattr(handler, '__name__', 'wrapped')
    return wrapper


@_gate
def blueprint_start(spec: str, plan: str, *, principal) -> dict:
    """ASYNC START. owner_id = principal.sub (Task Store tenant isolation)."""
    task = _store.create(owner_id=principal.sub)
    try:
        _store.update(task.task_id, status="running", stage="pipeline")
        # The reasoning+assembly pipeline runs here (live: Cloud Run Job via Cloud Tasks).
        from pipeline.orchestrator import run_pipeline
        result = run_pipeline(spec, plan, eraser_mcp=_ERASER_MCP)
        # Persist all blueprint artifacts to GCS + AlloyDB pointer (read back by blueprint_result).
        _ARTIFACT_STORE.write_blueprint(
            task.task_id, principal.sub, result["markdown"], result["json"],
            result.get("diagrams", []), _gcs_put=_GCS_PUT)
        # Task result holds only lightweight status; artifacts live in the store.
        _store.update(task.task_id, status="completed",
                      result={"artifacts_stored": True}, stage="done")
    except NotImplementedError as e:
        # Reasoning is wired to the live Gemini provider; this means the live path isn't
        # CONFIGURED in this environment (no credentials). See reasoning/llm_provider.py.
        _store.update(task.task_id, status="failed", error=f"reasoning_not_configured: {e}")
    except Exception as e:  # noqa: BLE001
        _store.update(task.task_id, status="failed", error=str(e))
    return {"taskId": task.task_id, "pollInterval": 5, "status": "queued"}


@_gate
def blueprint_status(taskId: str, *, principal) -> dict:
    t = _store.get(taskId)
    if not t:
        return {"status": "failed", "error": "unknown taskId"}
    if t.owner_id != principal.sub:                 # tenant isolation
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    return {"status": t.status, "stage": t.stage, "error": t.error}


@_gate
def blueprint_result(taskId: str, *, principal) -> dict:
    """Read all blueprint artifacts back from the store (GCS via AlloyDB pointer) and return
    md + json + diagrams (base64) to the IDE, combined into one response."""
    t = _store.get(taskId)
    if not t or t.status != "completed":
        return {"error": "not ready", "status": t.status if t else "unknown"}
    if t.owner_id != principal.sub:
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    ptr = _ARTIFACT_STORE.read_pointer(taskId)
    if not ptr or ptr.owner_id != principal.sub:
        return {"error": "artifacts not found"}
    blueprint = _ARTIFACT_STORE.read_blueprint(taskId, _gcs_get=_GCS_GET)
    return blueprint   # {markdown, json, diagrams[], gcs_prefix}


@_gate
def assemble_blueprint_tool(selections: dict, spec: str, plan: str, *, principal) -> dict:
    """Deterministic assembly (selections already validated). Builds md+json+DSL and runs the
    two-phase Eraser MCP render (submit DSL, then fetch .drawio.xml + .png). _ERASER_MCP is the
    injected Eraser MCP client (live transport is the seam)."""
    from assembly.assemble import assemble_blueprint, fetch_rendered_diagrams
    from assembly.selections import ArchitectureSelections
    result = assemble_blueprint(ArchitectureSelections(**selections), spec, plan, eraser_mcp=_ERASER_MCP)
    result = fetch_rendered_diagrams(result, eraser_mcp=_ERASER_MCP)
    return {"markdown": result.markdown, "json": result.json, "diagrams": result.diagrams}


@_gate
def validate_composition(agent_tree: dict, *, principal) -> dict:
    r = _validate_composition(agent_tree)
    return {"valid": r.valid, "violations": [{"rule": v.rule, "detail": v.detail} for v in r.violations]}


@_gate
def refresh(blueprint_md: str, drawio_files: dict, spec: str, plan: str,
            hashes_path: str, last_json: dict, *, principal) -> dict:
    from refresh.orchestrator import refresh as _refresh
    res = _refresh(blueprint_md, drawio_files, spec, plan, hashes_path, last_json)
    return {"sync_report": res.sync_report.__dict__,
            "structural_report": (res.structural_report.__dict__ if res.structural_report else None)}


TOOLS = {
    "blueprint_start": blueprint_start,
    "blueprint_status": blueprint_status,
    "blueprint_result": blueprint_result,
    "assemble_blueprint": assemble_blueprint_tool,
    "validate_composition": validate_composition,
    "refresh": refresh,
}


def serve():  # pragma: no cover - transport wiring
    """TODO(live): bind TOOLS to the MCP SDK transport on Cloud Run; pass the
    Authorization header from each MCP request into the handler as authorization_header."""
    raise NotImplementedError("Bind TOOLS to the MCP SDK transport (Cloud Run) + TLS 1.3.")
