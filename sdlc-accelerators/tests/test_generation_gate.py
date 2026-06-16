"""Path A generation gate: findings.md -> GCS + AlloyDB pointer -> server-side critical/high
check -> block with refresh message, or write tech-debt JSON per medium/low to GCS."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from findings_store.generation_gate import parse_findings_md, verify_generation_gate
from findings_store.store import FindingsStore

BLOCKING_MD = """# Findings
## 🔴 Critical (1)
- No cross-region DR strategy [§6]
## 🟠 High (1)
- WAF not using managed rule group [§5]
## 🟡 Medium (1)
- Angular 17 off radar [§4]
## ⚪ Low (1)
- Tighten latency [§9]
"""

CLEAN_MD = """# Findings
## 🔴 Critical (0)
_None._
## 🟠 High (0)
_None._
## 🟡 Medium (1)
- Angular 17 off radar [§4]
## ⚪ Low (1)
- Tighten latency [§9]
"""


def test_parse_findings_buckets():
    pf = parse_findings_md(BLOCKING_MD)
    assert len(pf.by_severity["critical"]) == 1
    assert len(pf.by_severity["high"]) == 1
    assert len(pf.blocking) == 2
    assert len(pf.non_blocking) == 2


def test_gate_blocks_on_critical_or_high():
    r = verify_generation_gate(BLOCKING_MD, "sarah@co", "task-12345678")
    assert r.signal == "stop"
    assert r.blocking_count == 2
    # message must instruct resolve + refresh + re-assess
    assert "/accelerator.refresh" in r.message
    assert "sync" in r.message and "diagram" in r.message


def test_gate_resumes_and_writes_tech_debt_when_only_medium_low():
    written = {}
    def gcs_put(uri, content):
        written[uri] = content
    r = verify_generation_gate(CLEAN_MD, "sarah@co", "task-12345678",
                               tech_debt_bucket="td-bucket", _gcs_put=gcs_put)
    assert r.signal == "resume"
    assert r.blocking_count == 0
    assert len(r.tech_debt_uris) == 2          # one per medium/low finding
    assert len(written) == 2
    # each is a valid tech-debt JSON
    for _uri, content in written.items():
        td = json.loads(content)
        assert td["status"] == "accepted"
        assert td["severity"] in ("medium", "low")
        assert td["tech_debt_id"].startswith("TD-")
        assert td["owner_id"] == "sarah@co"


def test_findings_store_gcs_uri_and_pointer():
    store = FindingsStore(bucket="findings-bucket")
    ptr = store.write_findings("task-9", "dev@co", BLOCKING_MD, has_blocking=True)
    assert ptr.gcs_uri == "gs://findings-bucket/findings/dev@co/task-9/findings.md"
    assert ptr.has_blocking is True
    # read back via pointer
    assert store.read_pointer("task-9").owner_id == "dev@co"
    assert store.read_findings_md("task-9") == BLOCKING_MD


def test_store_gcs_put_seam_invoked():
    store = FindingsStore(bucket="b")
    calls = []
    store.write_findings("t1", "o1", "md-content", has_blocking=False,
                         _gcs_put=lambda uri, content: calls.append((uri, content)))
    assert calls and calls[0][0].endswith("/findings.md")
    assert calls[0][1] == "md-content"
