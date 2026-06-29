"""Epic-to-Spec ingestion (Greenfield front door): Rally Epic -> signal-bearing spec.md.

Phase A (shaping.py)  — the one LlmAgent extracts span-traced signals into an Epic Signal Ledger.
Phase B (mapping.py)  — deterministic render to spec.md + fill-ratio confidence + Rally provenance.
orchestrator.run_ingest() ties them together; the server exposes ingest_epic_start/status/result.
"""

from __future__ import annotations
