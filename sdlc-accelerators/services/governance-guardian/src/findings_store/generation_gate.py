"""Server-side generation gate (Path A).

verify_generation_gate reads findings.md back via the AlloyDB pointer, parses the severity
categories, and:
  - if ANY critical or high finding remains -> signal "stop" + a message telling the developer
    to resolve them and run /accelerator.refresh to validate diagram/md sync, then re-assess.
  - if only medium/low remain -> signal "resume", and write each remaining finding as a
    tech-debt JSON object to a GCS bucket (one object per finding).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

BLOCKING = {"critical", "high"}
SEV_HEADER_RE = re.compile(r"^##\s*[^\w]*\s*(Critical|High|Medium|Low)\s*\((\d+)\)", re.IGNORECASE | re.MULTILINE)
BULLET_RE = re.compile(r"^- (.+?)(?:\s*\[(§?\d+)\])?\s*$", re.MULTILINE)


@dataclass
class ParsedFindings:
    by_severity: dict = field(default_factory=lambda: {"critical": [], "high": [], "medium": [], "low": []})

    @property
    def blocking(self) -> list:
        return self.by_severity["critical"] + self.by_severity["high"]

    @property
    def non_blocking(self) -> list:
        return self.by_severity["medium"] + self.by_severity["low"]


def parse_findings_md(findings_md: str) -> ParsedFindings:
    """Parse the findings.md (the Critical/High/Medium/Low grouped doc) into severity buckets."""
    pf = ParsedFindings()
    # Split into severity blocks by header, then collect bullets within each
    headers = list(SEV_HEADER_RE.finditer(findings_md))
    for i, h in enumerate(headers):
        sev = h.group(1).lower()
        start = h.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(findings_md)
        block = findings_md[start:end]
        for m in BULLET_RE.finditer(block):
            msg = m.group(1).strip()
            if msg and msg.lower() != "_none._":
                section = m.group(2) or ""
                pf.by_severity[sev].append({"message": msg, "section": section, "severity": sev})
    return pf


@dataclass
class GateResult:
    signal: str                       # "stop" | "resume"
    blocking_count: int
    message: str = ""
    tech_debt_uris: list = field(default_factory=list)


def _tech_debt_json(finding: dict, owner_id: str, task_id: str, idx: int) -> tuple[str, str]:
    """Build one tech-debt JSON object + its GCS object name."""
    td_id = f"TD-{time.strftime('%Y')}-{task_id[:8]}-{idx:03d}"
    obj = {
        "tech_debt_id": td_id,
        "severity": finding["severity"],
        "section": finding.get("section", ""),
        "message": finding["message"],
        "status": "accepted",
        "owner_id": owner_id,
        "task_id": task_id,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return td_id, json.dumps(obj, indent=2)


def verify_generation_gate(findings_md: str, owner_id: str, task_id: str,
                           tech_debt_bucket: str = "<TECH_DEBT_BUCKET>",
                           _gcs_put=None) -> GateResult:
    """The server-side gate. Reads parsed findings, blocks on critical/high, else writes tech debt."""
    pf = parse_findings_md(findings_md)
    blocking = pf.blocking

    if blocking:
        lines = [f"- [{f['severity'].upper()}]{(' ' + f['section']) if f['section'] else ''} {f['message']}"
                 for f in blocking]
        message = (
            f"❌ Generation blocked: {len(blocking)} critical/high finding(s) must be resolved first.\n\n"
            + "\n".join(lines)
            + "\n\nResolve these findings, then run `/accelerator.refresh` to validate that your "
              "diagram (.drawio.xml) and `app-blueprint.md` are back in sync, then re-run "
              "`/accelerator.assess` to confirm. Generation will remain blocked until no critical "
              "or high findings remain."
        )
        return GateResult(signal="stop", blocking_count=len(blocking), message=message)

    # No critical/high — write each remaining (medium/low) finding as a tech-debt JSON to GCS
    uris = []
    for idx, finding in enumerate(pf.non_blocking, start=1):
        td_id, td_json = _tech_debt_json(finding, owner_id, task_id, idx)
        obj_uri = f"gs://{tech_debt_bucket}/tech-debt/{owner_id}/{task_id}/{td_id}.json"
        if _gcs_put is not None:
            _gcs_put(obj_uri, td_json)
        uris.append(obj_uri)

    message = (
        f"✅ Governance gate passed: no critical or high findings. "
        f"{len(uris)} medium/low finding(s) recorded as accepted tech debt. Generating code..."
    )
    return GateResult(signal="resume", blocking_count=0, message=message, tech_debt_uris=uris)
