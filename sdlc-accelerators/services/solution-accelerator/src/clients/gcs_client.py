"""GCS client — object storage for blueprint artifacts, findings.md, and tech-debt JSON.

The stores (artifact_store, findings_store, generation_gate) take injectable _gcs_put/_gcs_get
callables. This client provides the real put/get with the live google-cloud-storage call written
but COMMENTED OUT, plus the in-memory reference backing used until it is wired.

Usage: pass `client.put` / `client.get` as the _gcs_put / _gcs_get seam to a store.
Per root CLAUDE.md, all external calls go through clients/base.with_retry.
"""
from __future__ import annotations

from collections.abc import Callable

from .base import with_retry


def _parse_gs_uri(uri: str) -> tuple[str, str]:
    """gs://bucket/path/to/obj -> (bucket, path/to/obj)."""
    rest = uri[len("gs://"):] if uri.startswith("gs://") else uri
    bucket, _, obj = rest.partition("/")
    return bucket, obj


class GcsClient:
    def __init__(self, _put: Callable[[str, bytes], None] | None = None,
                 _get: Callable[[str], bytes] | None = None):
        self._put_fn = _put
        self._get_fn = _get
        self._mem: dict[str, bytes] = {}   # in-memory reference backing

    def put(self, uri: str, data) -> None:
        """Write an object to GCS. Accepts bytes or str."""
        payload = data.encode() if isinstance(data, str) else data
        if self._put_fn is not None:
            with_retry(lambda: self._put_fn(uri, payload))
        else:
            self._live_put(uri, payload)

    def get(self, uri: str) -> bytes:
        """Read an object from GCS."""
        if self._get_fn is not None:
            return with_retry(lambda: self._get_fn(uri))
        return self._live_get(uri)

    def _live_put(self, uri: str, data: bytes) -> None:
        """The actual google-cloud-storage upload. COMMENTED OUT until wired.

        TO WIRE (checklist):
          1. `pip install google-cloud-storage`
          2. Credentials: Application Default Credentials (ADC) with the Storage Object Admin
             role on the target bucket(s).
          3. Ensure egress to storage.googleapis.com.
          4. Pre-create the buckets (blueprint, findings, tech-debt) with appropriate
             lifecycle/retention; bucket names are configured on the stores.
          5. Uncomment the body and wrap the upload in with_retry(...).
        """
        # from google.cloud import storage
        # bucket_name, blob_name = _parse_gs_uri(uri)
        # client = storage.Client()
        # bucket = client.bucket(bucket_name)
        # blob = bucket.blob(blob_name)
        # blob.upload_from_string(data)
        # return
        self._mem[uri] = data   # reference backing until the live call is uncommented

    def _live_get(self, uri: str) -> bytes:
        """The actual google-cloud-storage download. COMMENTED OUT until wired.
        Same wiring checklist as _live_put (Storage Object Viewer suffices for read)."""
        # from google.cloud import storage
        # bucket_name, blob_name = _parse_gs_uri(uri)
        # client = storage.Client()
        # blob = client.bucket(bucket_name).blob(blob_name)
        # return blob.download_as_bytes()
        if uri in self._mem:
            return self._mem[uri]
        raise NotImplementedError(
            "GCS live get is written but commented out in _live_get. Uncomment it "
            "(+ google-cloud-storage + credentials), or inject _get / use the put reference backing."
        )
