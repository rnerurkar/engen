"""Findings store — persists assessment findings.md to GCS with an AlloyDB pointer.

assess_result writes the findings.md to a GCS bucket and records a pointer row in AlloyDB
(task_id, owner_id, gcs_uri, has_blocking, created_at). The generate gate later reads the
findings back via this pointer to verify server-side that no critical/high findings remain.

GCS upload + AlloyDB insert are wired through clean interfaces (TODO live); the pointer
model, key scheme, and in-memory reference backing are real and tested.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class FindingsPointer:
    task_id: str
    owner_id: str
    gcs_uri: str                 # gs://<bucket>/findings/<owner>/<task_id>/findings.md
    has_blocking: bool           # any critical or high at write time (denormalized for fast gate)
    findings_md: str = ""        # kept for the in-memory reference backing; GCS holds the real copy
    created_at: float = field(default_factory=time.time)


class FindingsStore:
    """Reference backing. Production: GCS object + AlloyDB pointer row (RLS by owner_id)."""

    def __init__(self, bucket: str = "<FINDINGS_BUCKET>"):
        self.bucket = bucket
        self._pointers: dict[str, FindingsPointer] = {}   # AlloyDB table stand-in (keyed by task_id)

    def gcs_uri_for(self, owner_id: str, task_id: str) -> str:
        return f"gs://{self.bucket}/findings/{owner_id}/{task_id}/findings.md"

    def write_findings(self, task_id: str, owner_id: str, findings_md: str,
                       has_blocking: bool, _gcs_put=None) -> FindingsPointer:
        """Write findings.md to GCS and record the AlloyDB pointer.
        _gcs_put is the injectable upload seam (live: google.cloud.storage)."""
        uri = self.gcs_uri_for(owner_id, task_id)
        if _gcs_put is not None:
            _gcs_put(uri, findings_md)
        # else: in-memory reference keeps the content on the pointer
        ptr = FindingsPointer(task_id=task_id, owner_id=owner_id, gcs_uri=uri,
                              has_blocking=has_blocking, findings_md=findings_md)
        self._pointers[task_id] = ptr        # AlloyDB INSERT (live)
        return ptr

    def read_pointer(self, task_id: str) -> FindingsPointer | None:
        """Read the AlloyDB pointer row for a task."""
        return self._pointers.get(task_id)

    def read_findings_md(self, task_id: str, _gcs_get=None) -> str | None:
        """Read findings.md back via the pointer (live: GCS get from pointer.gcs_uri)."""
        ptr = self._pointers.get(task_id)
        if not ptr:
            return None
        if _gcs_get is not None:
            return _gcs_get(ptr.gcs_uri)
        return ptr.findings_md      # in-memory reference
