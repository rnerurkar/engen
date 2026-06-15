"""Blueprint artifact store — all blueprint artifacts in GCS, one pointer row in AlloyDB.

Mirrors the Governance Guardian findings store pattern. assemble (server-side) writes the
full artifact set to a GCS bucket under a per-task prefix and records ONE pointer row in
AlloyDB (task_id, owner_id, gcs_prefix, manifest). blueprint_result reads the pointer by
task_id and returns the artifacts to the IDE (md + json inline, diagrams as base64).

Artifacts stored:
  app-blueprint.md, app-blueprint.json,
  diagrams/<name>.drawio.xml, diagrams/<name>.png   (one pair per diagram)

Base64 PNGs go to GCS object storage, NOT into AlloyDB — AlloyDB holds only the small pointer.
GCS put/get are injectable seams; the pointer model, key scheme, and reference backing are real.
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field


@dataclass
class ArtifactManifest:
    """The list of artifact object names under the task's GCS prefix."""
    markdown: str = "app-blueprint.md"
    json: str = "app-blueprint.json"
    diagrams: list = field(default_factory=list)   # [{name, drawio_xml_obj, png_obj}]


@dataclass
class BlueprintPointer:
    task_id: str
    owner_id: str
    gcs_prefix: str                  # gs://<bucket>/blueprints/<owner>/<task_id>/
    manifest: ArtifactManifest
    created_at: float = field(default_factory=time.time)


class BlueprintArtifactStore:
    """Reference backing. Production: GCS objects + AlloyDB pointer row (RLS by owner_id)."""

    def __init__(self, bucket: str = "<BLUEPRINT_BUCKET>"):
        self.bucket = bucket
        self._pointers: dict[str, BlueprintPointer] = {}   # AlloyDB table stand-in
        self._objects: dict[str, bytes] = {}               # in-memory GCS stand-in

    def prefix_for(self, owner_id: str, task_id: str) -> str:
        return f"gs://{self.bucket}/blueprints/{owner_id}/{task_id}/"

    def _put(self, uri: str, data: bytes, _gcs_put=None):
        if _gcs_put is not None:
            _gcs_put(uri, data)
        else:
            self._objects[uri] = data

    def _get(self, uri: str, _gcs_get=None) -> bytes | None:
        if _gcs_get is not None:
            return _gcs_get(uri)
        return self._objects.get(uri)

    def write_blueprint(self, task_id: str, owner_id: str, markdown: str, json_doc: dict,
                        diagrams: list, _gcs_put=None) -> BlueprintPointer:
        """Write all artifacts to GCS and record the single AlloyDB pointer.
        diagrams: [{name, drawio_xml, png_base64}]."""
        prefix = self.prefix_for(owner_id, task_id)
        manifest = ArtifactManifest()

        self._put(prefix + manifest.markdown, markdown.encode(), _gcs_put)
        self._put(prefix + manifest.json, json.dumps(json_doc, indent=2).encode(), _gcs_put)

        for d in diagrams:
            name = d["name"]
            drawio_obj = f"diagrams/{name}.drawio.xml"
            png_obj = f"diagrams/{name}.png"
            self._put(prefix + drawio_obj, (d.get("drawio_xml") or "").encode(), _gcs_put)
            # png stored as decoded bytes in GCS (base64 only for transport)
            png_b64 = d.get("png_base64") or ""
            png_bytes = base64.b64decode(png_b64) if png_b64 else b""
            self._put(prefix + png_obj, png_bytes, _gcs_put)
            manifest.diagrams.append({"name": name, "drawio_xml_obj": drawio_obj, "png_obj": png_obj})

        ptr = BlueprintPointer(task_id=task_id, owner_id=owner_id, gcs_prefix=prefix, manifest=manifest)
        self._pointers[task_id] = ptr      # AlloyDB INSERT (live)
        return ptr

    def read_pointer(self, task_id: str) -> BlueprintPointer | None:
        return self._pointers.get(task_id)

    def read_blueprint(self, task_id: str, _gcs_get=None) -> dict | None:
        """Read all artifacts back via the pointer. Returns md + json inline, diagrams as base64."""
        ptr = self._pointers.get(task_id)
        if not ptr:
            return None
        p = ptr.gcs_prefix
        md = self._get(p + ptr.manifest.markdown, _gcs_get)
        js = self._get(p + ptr.manifest.json, _gcs_get)
        diagrams = []
        for d in ptr.manifest.diagrams:
            drawio = self._get(p + d["drawio_xml_obj"], _gcs_get) or b""
            png = self._get(p + d["png_obj"], _gcs_get) or b""
            diagrams.append({
                "name": d["name"],
                "drawio_xml": drawio.decode() if isinstance(drawio, bytes) else drawio,
                "png_base64": base64.b64encode(png).decode() if png else "",
                "gcs_uri": p + d["png_obj"],
            })
        return {
            "markdown": md.decode() if isinstance(md, bytes) else md,
            "json": json.loads(js) if js else None,
            "diagrams": diagrams,
            "gcs_prefix": p,
        }
