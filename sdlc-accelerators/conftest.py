"""Root pytest conftest — registers every source root on sys.path once.

This replaces the per-file `sys.path.insert` bootstrapping in individual test files. The repo
uses a multi-service `src` layout (each service and the brownfield module ship their own `src`),
so there is no single installable package; this conftest centralizes the path setup that the
runtime modules also perform, so tests import cleanly without ad-hoc path hacks.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

_SRC_ROOTS = [
    # `src`-on-path services (import as bare top-level modules, e.g. `from clients...`)
    _ROOT / "services/solution-accelerator/src",
    _ROOT / "services/governance-guardian/src",
    _ROOT / "services/mcp-auth/src",
    _ROOT / "services/catalog-ingestion/src",
    _ROOT / "services/evalops/src",
    _ROOT / "services/prs-scanner/src",
    _ROOT / "brownfield/src",
    # service-dir-on-path services (import as `from src.<pkg>...`, e.g. accelerator-cli)
    _ROOT / "services/accelerator-cli",
]

for _p in _SRC_ROOTS:
    if _p.is_dir():
        sp = str(_p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
