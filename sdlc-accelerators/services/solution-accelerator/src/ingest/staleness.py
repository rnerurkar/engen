"""Epic staleness detection (M-1).

The Epic-to-Spec front door stamps Rally provenance (FormattedID + ObjectVersion) in two places:
  - the `spec.md` provenance header (human-visible, but EDITABLE — a developer could delete it), and
  - `epic-signal-ledger.json` (the durable sidecar — the authoritative source for drift checks).

`/accelerator.refresh` uses these helpers to decide whether the spec is stale relative to the current
Rally Epic: it reads the stamped ObjectVersion (preferring the ledger sidecar) and compares it to the
ObjectVersion the coding agent just fetched from the Rally MCP server. This module is deterministic and
unit-testable; it does NOT call Rally (the coding agent passes the current ObjectVersion in).
"""

from __future__ import annotations

import json
import re
from typing import Any

_HEADER_FID = re.compile(r"Epic[:\s]+(?P<fid>[A-Za-z]+\d+)", re.IGNORECASE)
_HEADER_OV = re.compile(r"ObjectVersion[:\s]+(?P<ov>\d+)", re.IGNORECASE)


def read_provenance_from_ledger(
    ledger_json: str | dict[str, Any],
) -> dict[str, Any] | None:
    """Authoritative: read {formatted_id, object_version} from epic-signal-ledger.json (durable sidecar)."""
    data = json.loads(ledger_json) if isinstance(ledger_json, str) else ledger_json
    prov = (data or {}).get("provenance") or {}
    fid = prov.get("formatted_id") or prov.get("formattedId")
    ov = prov.get("object_version", prov.get("objectVersion"))
    if fid is None and ov is None:
        return None
    return {"formatted_id": fid, "object_version": None if ov is None else int(ov)}


def read_provenance_from_spec(spec_md: str) -> dict[str, Any] | None:
    """Fallback: parse the spec.md provenance header. Editable, so prefer the ledger when available."""
    fid = _HEADER_FID.search(spec_md or "")
    ov = _HEADER_OV.search(spec_md or "")
    if not fid and not ov:
        return None
    return {
        "formatted_id": fid.group("fid") if fid else None,
        "object_version": int(ov.group("ov")) if ov else None,
    }


def read_provenance(
    spec_md: str | None = None, ledger_json: Any = None
) -> dict[str, Any] | None:
    """Prefer the durable ledger sidecar; fall back to the (editable) spec header."""
    if ledger_json is not None:
        prov = read_provenance_from_ledger(ledger_json)
        if prov:
            return prov
    return read_provenance_from_spec(spec_md or "")


def is_stale(stamped_object_version: Any, current_object_version: Any) -> bool:
    """True when the current Rally ObjectVersion is newer than the one the spec was generated from.

    Conservative: if either value is missing/unparseable, treat as stale so the developer re-checks.
    """
    try:
        return int(current_object_version) > int(stamped_object_version)
    except (TypeError, ValueError):
        return True
