"""Refresh Step 0 — DETECT what changed.

Compares current .md / .drawio SHA-256 against .accelerator-hashes (last-known state)
and classifies into Case A (only .md), B (only .drawio), C (both), or NONE.

Per ARB M-1: spec.md and plan.md are read from the workspace automatically — the
developer does not pass them. This module works on file content, not params.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast


class Case(str, Enum):
    NONE = "NONE"
    A = "A"  # only .md changed
    B = "B"  # only .drawio changed
    C = "C"  # both changed


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass
class ChangeDetection:
    case: Case
    md_changed: bool
    drawio_changed: bool
    last_hashes: dict[str, Any]


def load_hashes(hashes_path: str) -> dict[str, Any]:
    p = Path(hashes_path)
    if not p.exists():
        return {}
    return cast("dict[str, Any]", json.loads(p.read_text()))


def detect(
    blueprint_md: str, drawio_files: dict[str, str], hashes_path: str
) -> ChangeDetection:
    """blueprint_md: current .md content. drawio_files: {filename: xml content}.
    Compares SHA against .accelerator-hashes (more robust than timestamps for content)."""
    last = load_hashes(hashes_path)
    md_changed = sha256(blueprint_md) != last.get("md")
    drawio_last = last.get("drawio", {})
    drawio_changed = any(
        sha256(xml) != drawio_last.get(name) for name, xml in drawio_files.items()
    )

    if md_changed and drawio_changed:
        case = Case.C
    elif md_changed:
        case = Case.A
    elif drawio_changed:
        case = Case.B
    else:
        case = Case.NONE
    return ChangeDetection(
        case=case,
        md_changed=md_changed,
        drawio_changed=drawio_changed,
        last_hashes=last,
    )


def write_hashes(
    hashes_path: str,
    blueprint_md: str,
    drawio_files: dict[str, str],
    json_doc: dict[str, Any],
) -> dict[str, Any]:
    """Update .accelerator-hashes after a successful sync."""
    hashes = {
        "md": sha256(blueprint_md),
        "drawio": {name: sha256(xml) for name, xml in drawio_files.items()},
        "json": sha256(json.dumps(json_doc, sort_keys=True)),
    }
    Path(hashes_path).write_text(json.dumps(hashes, indent=2))
    return hashes
