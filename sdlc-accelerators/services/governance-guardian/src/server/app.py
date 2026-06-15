"""Governance Guardian MCP Server — assess lifecycle, OAuth 2.1 + Entra ID protected.

Exposes: assess_start, assess_status, assess_result, recordTechDebt.
Same auth as Solution Accelerator (same token, same scope, same SA group) — a developer
authenticated for one does NOT re-authenticate for the other. owner_id tenant isolation.

The per-section assessment uses the Eraser MCP server (placeholder seam).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "mcp-auth", "src"))

import importlib.util as _ilu
import os as _os

_ts_spec = _ilu.spec_from_file_location('gg_task_store', _os.path.join(_os.path.dirname(__file__), 'task_store.py'))
_ts = _ilu.module_from_spec(_ts_spec)
import sys as _sys

_sys.modules[_ts_spec.name] = _ts
_ts_spec.loader.exec_module(_ts)
AssessTaskStore = _ts.AssessTaskStore
from assessment.engine import classify_finding
from assessment.eraser_assess import assess_blueprint_via_eraser
from findings_store.generation_gate import verify_generation_gate as _verify_gate
from findings_store.store import FindingsStore
from oauth_config import OAuthConfig  # type: ignore

_store = AssessTaskStore()
_CFG = OAuthConfig.from_env()
_DECODE = None
_ERASER_MCP = None  # injected Eraser MCP client (placeholder seam)
_FINDINGS_STORE = FindingsStore()        # findings.md -> GCS + AlloyDB pointer
_TECH_DEBT_BUCKET = '<TECH_DEBT_BUCKET>'  # tech-debt JSON objects bucket
_GCS_PUT = None                           # injectable GCS upload seam (live: google.cloud.storage)
_GCS_GET = None                           # injectable GCS download seam


def _gate(handler):
    def wrapper(*args, authorization_header=None, **kwargs):
        from middleware import authenticate as _auth
        auth = _auth(authorization_header, _CFG, _decode=_DECODE)
        if not auth.ok:
            return {'_auth_error': True, 'status': auth.status, 'headers': auth.headers, 'body': auth.body}
        return handler(*args, principal=auth.principal, **kwargs)
    wrapper.__name__ = getattr(handler, '__name__', 'wrapped')
    return wrapper


def _run_assessment(blueprint_md: str, assets_dir: str = ".") -> dict:
    """PDF round-trip: md -> PDF -> Eraser MCP -> findings PDF -> MD (Critical/High/Medium/Low).
    Returns findings_md for the IDE plus structured findings with showstopper classification."""
    result = assess_blueprint_via_eraser(blueprint_md, assets_dir=assets_dir, eraser_mcp=_ERASER_MCP)
    classified = []
    for i, f in enumerate(result["findings"], start=1):
        classified.append({
            "id": f"F-{i}", "section": f.get("section", ""), "severity": f["severity"],
            "classification": classify_finding(f["severity"]), "message": f["message"],
        })
    has_showstopper = any(c["classification"] == "showstopper" for c in classified)
    return {
        "findings_md": result["findings_md"],   # returned to the IDE
        "scorecard": result["scorecard"],
        "findings": classified,
        "signal": "stop" if has_showstopper else "resume",
    }


@_gate
def assess_start(solution_package: dict, *, principal) -> dict:
    """ASYNC START. solution_package carries app-blueprint.md. owner_id = principal.sub."""
    task = _store.create(owner_id=principal.sub)
    try:
        _store.update(task.task_id, status="running", stage="assessing")
        result = _run_assessment(solution_package.get("blueprint_md", ""))
        _store.update(task.task_id, status="completed", result=result, stage="done")
    except NotImplementedError as e:
        _store.update(task.task_id, status="failed", error=f"eraser_mcp_not_wired: {e}")
    except Exception as e:  # noqa: BLE001
        _store.update(task.task_id, status="failed", error=str(e))
    return {"taskId": task.task_id, "pollInterval": 5, "status": "queued"}


@_gate
def assess_status(taskId: str, *, principal) -> dict:
    t = _store.get(taskId)
    if not t:
        return {"status": "failed", "error": "unknown taskId"}
    if t.owner_id != principal.sub:
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    return {"status": t.status, "stage": t.stage, "error": t.error}


@_gate
def assess_result(taskId: str, *, principal) -> dict:
    t = _store.get(taskId)
    if not t or t.status != "completed":
        return {"error": "not ready", "status": t.status if t else "unknown"}
    if t.owner_id != principal.sub:
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    # Persist findings.md to GCS + AlloyDB pointer (read back by the generation gate).
    result = t.result
    has_blocking = any(f["severity"] in ("critical", "high") for f in result.get("findings", []))
    _FINDINGS_STORE.write_findings(taskId, principal.sub, result.get("findings_md", ""),
                                   has_blocking, _gcs_put=_GCS_PUT)
    return result


@_gate
def verify_generation_gate(taskId: str, *, principal) -> dict:
    """Server-side generate gate. Looks up the findings pointer in AlloyDB, gets the GCS URL
    to findings.md, reads it back from GCS, and determines whether any Critical/High remain:
      - Critical/High remain  -> {signal: stop} directing the dev to resolve + /accelerator.refresh.
      - Only Medium/Low remain -> writes tech-debt JSON per finding to GCS, {signal: resume}.
    """
    ptr = _FINDINGS_STORE.read_pointer(taskId)              # AlloyDB pointer lookup
    if not ptr:
        return {"signal": "stop", "message": "No assessment findings found for this task. "
                "Run /accelerator.assess first."}
    if ptr.owner_id != principal.sub:
        return {"_auth_error": True, "status": 403,
                "body": {"error": "forbidden", "error_description": "Not your task"}}
    # Pointer carries the GCS URL; read findings.md back from GCS via that URL.
    findings_md = _FINDINGS_STORE.read_findings_md(taskId, _gcs_get=_GCS_GET)
    gate = _verify_gate(findings_md, principal.sub, taskId,
                        tech_debt_bucket=_TECH_DEBT_BUCKET, _gcs_put=_GCS_PUT)
    return {"signal": gate.signal, "blocking_count": gate.blocking_count,
            "message": gate.message, "tech_debt_uris": gate.tech_debt_uris,
            "findings_gcs_uri": ptr.gcs_uri}


@_gate
def recordTechDebt(findings: list, *, principal) -> dict:
    """Record non-showstopper findings as tech debt; return resume/stop signal."""
    showstoppers = [f for f in findings if f.get("classification") == "showstopper"]
    tech_debt = [f for f in findings if f.get("classification") == "tech_debt"]
    return {
        "signal": "stop" if showstoppers else "resume",
        "tech_debt_ids": [f.get("id") for f in tech_debt],
        "recorded_by": principal.sub,
    }


TOOLS = {
    "assess_start": assess_start,
    "assess_status": assess_status,
    "assess_result": assess_result,
    "recordTechDebt": recordTechDebt,
    "verify_generation_gate": verify_generation_gate,
}


def serve():  # pragma: no cover
    """TODO(live): bind TOOLS to the MCP SDK transport on Cloud Run; pass each request's
    Authorization header into the handler. Same Entra config/scope as Solution Accelerator."""
    raise NotImplementedError("Bind TOOLS to the MCP SDK transport (Cloud Run) + TLS 1.3.")
