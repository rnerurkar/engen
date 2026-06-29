"""Brownfield Epic staleness detection (mirrors greenfield M-1 fix).

Provenance is stamped in the spec.md header (editable) and in epic-signal-ledger.json (durable sidecar).
`/accelerator.refresh` prefers the sidecar. Deterministic and unit-testable; does not call Rally.
"""

from __future__ import annotations

import json
import re
from typing import Any

# L-2: anchored to the provenance phrasing the mapping emits ("Rally Epic `E…`" / "ObjectVersion `N`")
# so a bare mention of the word "Epic" in the spec body cannot be mis-parsed as provenance.
_HEADER_FID = re.compile(r"Rally\s+Epic[`:\s]+(?P<fid>[A-Za-z]+\d+)", re.IGNORECASE)
_HEADER_OV = re.compile(r"ObjectVersion[`:\s]+(?P<ov>\d+)", re.IGNORECASE)
_HEADER_CSA = re.compile(r"architecture\.md\s+@\s+`(?P<csa>[0-9a-f]+)`", re.IGNORECASE)


def read_provenance_from_ledger(
    ledger_json: str | dict[str, Any],
) -> dict[str, Any] | None:
    data = json.loads(ledger_json) if isinstance(ledger_json, str) else ledger_json
    prov = (data or {}).get("provenance") or {}
    fid = prov.get("formatted_id") or prov.get("formattedId")
    ov = prov.get("object_version", prov.get("objectVersion"))
    csa = prov.get("csa_hash") or ""
    if fid is None and ov is None:
        return None
    return {
        "formatted_id": fid,
        "object_version": None if ov is None else int(ov),
        "csa_hash": csa,
    }


def read_provenance_from_spec(spec_md: str) -> dict[str, Any] | None:
    fid = _HEADER_FID.search(spec_md or "")
    ov = _HEADER_OV.search(spec_md or "")
    csa = _HEADER_CSA.search(spec_md or "")
    if not fid and not ov:
        return None
    return {
        "formatted_id": fid.group("fid") if fid else None,
        "object_version": int(ov.group("ov")) if ov else None,
        "csa_hash": csa.group("csa") if csa else "",
    }


def read_provenance(
    spec_md: str | None = None, ledger_json: Any = None
) -> dict[str, Any] | None:
    if ledger_json is not None:
        prov = read_provenance_from_ledger(ledger_json)
        if prov:
            return prov
    return read_provenance_from_spec(spec_md or "")


def is_stale(stamped_object_version: Any, current_object_version: Any) -> bool:
    try:
        return int(current_object_version) > int(stamped_object_version)
    except (TypeError, ValueError):
        return True
