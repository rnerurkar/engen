"""Repo-root source-path bootstrap.

The repo uses a multi-service `src` layout with no installable package, so cross-service imports
need the sibling `src` roots on sys.path. Historically every consumer did its own fragile
`sys.path.insert(os.path.dirname(os.path.dirname(__file__)))` chain. This module centralizes that:
call `ensure(*names)` to put the named service src roots on the path exactly once.

Intra-package imports (a module finding its OWN src) remain a local convention; this module is for
the genuinely cross-service reaches (e.g. brownfield → solution-accelerator, servers → mcp-auth).
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

_KNOWN = {
    "solution-accelerator": _ROOT / "services/solution-accelerator/src",
    "governance-guardian": _ROOT / "services/governance-guardian/src",
    "mcp-auth": _ROOT / "services/mcp-auth/src",
    "brownfield": _ROOT / "brownfield/src",
}


def ensure(*names: str) -> None:
    """Register the named service src roots on sys.path (idempotent)."""
    for name in names:
        p = _KNOWN.get(name)
        if p and p.is_dir():
            sp = str(p)
            if sp not in sys.path:
                sys.path.insert(0, sp)
