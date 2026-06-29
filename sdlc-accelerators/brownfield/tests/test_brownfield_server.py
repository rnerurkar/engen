"""Brownfield MCP server: async blueprint_start/status/result, OAuth gating, owner_id isolation,
and read-back from the design-contract store. Reuses the platform's mcp-auth library."""

import importlib.util
import json
import sys
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

import oauth_config as oc  # noqa: E402

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIV = _KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
_PUB = _KEY.public_key()

CFG = oc.OAuthConfig(
    tenant_id="t",
    client_id="c",
    audience="api://sdlc-accelerators",
    required_scope="sdlc-accelerators.mcp",
    required_group_id="SA-GROUP",
    authorize_endpoint="https://login.microsoftonline.com/t/oauth2/v2.0/authorize",
    token_endpoint="x",
    jwks_uri="x",
    issuer="https://login.microsoftonline.com/t/v2.0",
)


def _token(sub="sarah@company.com", groups=("SA-GROUP",)):
    return jwt.encode(
        {
            "sub": sub,
            "name": "S",
            "aud": CFG.audience,
            "iss": CFG.issuer,
            "exp": int(time.time()) + 3600,
            "scp": "sdlc-accelerators.mcp",
            "groups": list(groups),
        },
        _PRIV,
        algorithm="RS256",
    )


def _decode(tok):
    return jwt.decode(
        tok,
        _PUB,
        algorithms=["RS256"],
        audience=CFG.audience,
        issuer=CFG.issuer,
        options={"require": ["exp", "sub", "aud", "iss"]},
    )


def _server():
    spec = importlib.util.spec_from_file_location(
        "bf_server", ROOT / "src/brownfield/server/app.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["bf_server"] = m
    spec.loader.exec_module(m)
    m._CFG = CFG
    m._DECODE = _decode
    # load the reference substitution rows + a recommend stub
    from brownfield.map_current_to_target import SubstitutionRow

    rows = json.loads(
        (
            ROOT / "examples/vsphere-mpa-aws-spa/inputs/substitution-table.json"
        ).read_text()
    )["rows"]
    m._SUBSTITUTION_ROWS = [SubstitutionRow(**r) for r in rows]
    m._RECOMMEND_FN = lambda s: {
        "pattern_ref": s["transition_pattern_ref"],
        "confidence": 0.9,
        "requires_review": False,
    }
    return m


REF = ROOT / "examples/vsphere-mpa-aws-spa/inputs"


def test_missing_token_401():
    m = _server()
    r = m.blueprint_start("spec", "plan", authorization_header=None)
    assert r["_auth_error"] is True and r["status"] == 401


def test_full_async_flow_start_status_result():
    m = _server()
    spec, plan = (REF / "spec.md").read_text(), (REF / "plan.md").read_text()
    start = m.blueprint_start(spec, plan, authorization_header="Bearer " + _token())
    tid = start["taskId"]
    assert start["status"] == "completed"
    status = m.blueprint_status(tid, authorization_header="Bearer " + _token())
    assert status["status"] == "completed"
    result = m.blueprint_result(tid, authorization_header="Bearer " + _token())
    # read back from the contract store
    assert result["design_contract"]["schema_version"] == "2.0"
    assert result["design_contract"]["lifecycle"] == "LIVE"
    assert len(result["diagrams"]) == 4
    assert result["blueprint_md"].startswith("# Brownfield Migration Blueprint")


def test_owner_isolation_on_result():
    m = _server()
    start = m.blueprint_start(
        (REF / "spec.md").read_text(),
        (REF / "plan.md").read_text(),
        authorization_header="Bearer " + _token(sub="alice@co"),
    )
    tid = start["taskId"]
    # a different user cannot read alice's task
    r = m.blueprint_result(tid, authorization_header="Bearer " + _token(sub="bob@co"))
    assert r.get("_auth_error") is True and r["status"] == 403


def test_readiness_block_surfaces_as_failed():
    m = _server()
    bad_spec = """## Integration Inventory
### Integration: INT-001 — x
- **Technology + version:**
- **Integration type:** nope
- **Data flow direction:** nope
- **Criticality:** nope
- **Coexistence constraint:** nope
- **API surface / contract:** none
- **State management:**
- **Data volume + SLA:**
"""
    start = m.blueprint_start(
        bad_spec,
        "### Integration: INT-001 — x\n- **R-factor:** refactor\n",
        authorization_header="Bearer " + _token(),
    )
    assert start["status"] == "failed"
    status = m.blueprint_status(
        start["taskId"], authorization_header="Bearer " + _token()
    )
    assert status["status"] == "failed"


def test_non_sa_group_forbidden():
    m = _server()
    r = m.blueprint_start(
        "spec", "plan", authorization_header="Bearer " + _token(groups=("other",))
    )
    assert r["_auth_error"] is True and r["status"] == 403
