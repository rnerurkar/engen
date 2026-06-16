"""GCS client for Governance Guardian — re-exports the canonical implementation.

The GCS client logic lives once in solution-accelerator (clients/gcs_client.py). This module
re-exports it so Governance Guardian code can `from gcs_client import GcsClient` without keeping a
byte-for-byte duplicate (which risks divergence). Path resolution uses the centralized bootstrap.
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import _srcpaths  # noqa: E402

_srcpaths.ensure("solution-accelerator")

from clients.gcs_client import GcsClient, _parse_gs_uri  # noqa: E402,F401
