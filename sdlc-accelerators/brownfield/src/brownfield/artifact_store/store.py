"""Brownfield design-contract artifact store — GCS objects + one AlloyDB pointer per task.

Mirrors greenfield's BlueprintArtifactStore. The brownfield pipeline assembles app-blueprint.md,
design_contract.json (v2.0), and four diagram DSLs; this store persists them to a GCS bucket under
a per-task prefix and records ONE pointer row in AlloyDB (task_id, owner_id, gcs_prefix, manifest).
blueprint_result reads the pointer by task_id (owner_id-isolated) and returns the artifacts.

GCS put/get are injectable seams; the pointer model, key scheme, and reference backing are real.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, cast


@dataclass
class ContractManifest:
    markdown: str = "app-blueprint.md"
    contract: str = "design_contract.json"
    diagrams: list[Any] = field(default_factory=list)  # [{name, dsl_obj}]


@dataclass
class ContractPointer:
    task_id: str
    owner_id: str
    gcs_prefix: str  # gs://<bucket>/contracts/<owner>/<task_id>/
    manifest: ContractManifest
    created_at: float = field(default_factory=time.time)


class DesignContractStore:
    """Reference backing. Production: GCS objects + AlloyDB pointer row (RLS by owner_id)."""

    def __init__(self, bucket: str = "<BROWNFIELD_CONTRACT_BUCKET>") -> None:
        self.bucket = bucket
        self._pointers: dict[str, ContractPointer] = {}  # AlloyDB table stand-in
        self._objects: dict[str, bytes] = {}  # in-memory GCS stand-in

    def prefix_for(self, owner_id: str, task_id: str) -> str:
        return f"gs://{self.bucket}/contracts/{owner_id}/{task_id}/"

    def _put(self, uri: str, data: bytes, _gcs_put: Any = None) -> None:
        if _gcs_put is not None:
            _gcs_put(uri, data)
        else:
            self._objects[uri] = data

    def _get(self, uri: str, _gcs_get: Any = None) -> bytes | None:
        if _gcs_get is not None:
            return cast("bytes | None", _gcs_get(uri))
        return self._objects.get(uri)

    def write_contract(
        self,
        task_id: str,
        owner_id: str,
        blueprint_md: str,
        design_contract: dict[str, Any],
        diagrams: list[Any],
        _gcs_put: Any = None,
    ) -> ContractPointer:
        """Write blueprint md + design_contract.json + diagram DSLs to GCS; record the AlloyDB pointer.
        diagrams: [{name, dsl}]."""
        prefix = self.prefix_for(owner_id, task_id)
        manifest = ContractManifest()
        self._put(prefix + manifest.markdown, blueprint_md.encode(), _gcs_put)
        self._put(
            prefix + manifest.contract,
            json.dumps(design_contract, indent=2).encode(),
            _gcs_put,
        )
        for d in diagrams:
            dsl_obj = f"diagrams/{d['name']}.dsl"
            self._put(prefix + dsl_obj, (d.get("dsl") or "").encode(), _gcs_put)
            manifest.diagrams.append({"name": d["name"], "dsl_obj": dsl_obj})
        ptr = ContractPointer(
            task_id=task_id, owner_id=owner_id, gcs_prefix=prefix, manifest=manifest
        )
        self._pointers[task_id] = ptr  # AlloyDB INSERT (live)
        return ptr

    def read_pointer(self, task_id: str) -> ContractPointer | None:
        return self._pointers.get(task_id)

    def read_contract(
        self, task_id: str, _gcs_get: Any = None
    ) -> dict[str, Any] | None:
        """Read all artifacts back via the pointer. Returns md + contract inline + diagram DSLs."""
        ptr = self._pointers.get(task_id)
        if not ptr:
            return None
        p = ptr.gcs_prefix
        md = self._get(p + ptr.manifest.markdown, _gcs_get)
        cj = self._get(p + ptr.manifest.contract, _gcs_get)
        diagrams = []
        for d in ptr.manifest.diagrams:
            dsl = self._get(p + d["dsl_obj"], _gcs_get) or b""
            diagrams.append(
                {
                    "name": d["name"],
                    "dsl": dsl.decode() if isinstance(dsl, bytes) else dsl,
                    "gcs_uri": p + d["dsl_obj"],
                }
            )
        return {
            "blueprint_md": md.decode() if isinstance(md, bytes) else md,
            "design_contract": json.loads(cj) if cj else None,
            "diagrams": diagrams,
            "gcs_prefix": p,
        }
