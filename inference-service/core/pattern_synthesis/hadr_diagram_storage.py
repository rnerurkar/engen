"""
HA/DR Diagram Storage — GCS Edition
------------------------------------
Uploads SVG, draw.io XML, and PNG diagram artefacts to a GCS bucket
organised by pattern name, DR strategy, and lifecycle phase.

GCS path structure:
  patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.svg
  patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.drawio
  patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.png

Provides signed URLs for time-limited access and public URLs for
embedding in SharePoint pages.
"""

import logging
import re
from typing import Dict, Optional, Tuple

from google.cloud import storage as gcs

logger = logging.getLogger(__name__)


class HADRDiagramStorage:
    """
    Manages uploading and retrieving HA/DR diagram artefacts on GCS.
    """

    # Content-type mapping for diagram artefacts
    CONTENT_TYPES = {
        "svg": "image/svg+xml",
        "drawio": "application/xml",
        "png": "image/png",
    }

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Args:
            bucket_name: GCS bucket name for diagram storage.
            project_id:  GCP project ID (used for client initialisation).
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self._init_client()

    def _init_client(self):
        try:
            self.client = gcs.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(
                f"HADRDiagramStorage initialised — bucket={self.bucket_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialise GCS client: {e}")
            self.client = None
            self.bucket = None

    # ─── Path helpers ────────────────────────────────────────────────────

    @staticmethod
    def _safe_name(name: str) -> str:
        """Sanitise a name for use in GCS object paths."""
        safe = re.sub(r"[^\w\s-]", "", name)
        safe = re.sub(r"[\s]+", "-", safe).strip("-").lower()
        return safe or "unnamed"

    def _build_prefix(
        self, pattern_name: str, strategy: str, phase: str
    ) -> str:
        """Build the GCS path prefix for a given diagram."""
        return (
            f"patterns/{self._safe_name(pattern_name)}"
            f"/hadr-diagrams"
            f"/{self._safe_name(strategy)}"
            f"/{self._safe_name(phase)}"
        )

    # ─── Upload methods ──────────────────────────────────────────────────

    def upload_diagram_bundle(
        self,
        pattern_name: str,
        strategy: str,
        phase: str,
        svg_content: str,
        drawio_xml: str,
        png_bytes: bytes,
    ) -> Dict[str, str]:
        """
        Upload all three artefacts (SVG, draw.io XML, PNG) for one diagram.

        Returns:
            Dict with keys ``svg_url``, ``drawio_url``, ``png_url`` pointing
            to the public GCS URLs.  Empty strings on failure.
        """
        urls: Dict[str, str] = {
            "svg_url": "",
            "drawio_url": "",
            "png_url": "",
        }

        if not self.bucket:
            logger.error("GCS bucket not available — cannot upload diagrams")
            return urls

        prefix = self._build_prefix(pattern_name, strategy, phase)

        # SVG
        if svg_content:
            urls["svg_url"] = self._upload_text(
                f"{prefix}.svg", svg_content, "svg"
            )

        # draw.io XML
        if drawio_xml:
            urls["drawio_url"] = self._upload_text(
                f"{prefix}.drawio", drawio_xml, "drawio"
            )

        # PNG
        if png_bytes:
            urls["png_url"] = self._upload_bytes(
                f"{prefix}.png", png_bytes, "png"
            )

        logger.info(
            f"Uploaded diagram bundle: {prefix} "
            f"(svg={bool(urls['svg_url'])}, "
            f"drawio={bool(urls['drawio_url'])}, "
            f"png={bool(urls['png_url'])})"
        )
        return urls

    def _upload_text(
        self, blob_path: str, content: str, artefact_type: str
    ) -> str:
        """Upload a text artefact and return its public URL."""
        try:
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                content,
                content_type=self.CONTENT_TYPES.get(artefact_type, "text/plain"),
            )
            # Make publicly readable for embedding
            blob.make_public()
            logger.debug(f"Uploaded {artefact_type}: gs://{self.bucket_name}/{blob_path}")
            return blob.public_url
        except Exception as e:
            logger.error(f"Upload failed for {blob_path}: {e}")
            return ""

    def _upload_bytes(
        self, blob_path: str, data: bytes, artefact_type: str
    ) -> str:
        """Upload a binary artefact and return its public URL."""
        try:
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(
                data,
                content_type=self.CONTENT_TYPES.get(artefact_type, "application/octet-stream"),
            )
            blob.make_public()
            logger.debug(f"Uploaded {artefact_type}: gs://{self.bucket_name}/{blob_path}")
            return blob.public_url
        except Exception as e:
            logger.error(f"Upload failed for {blob_path}: {e}")
            return ""

    # ─── Retrieval helpers ───────────────────────────────────────────────

    def get_signed_url(
        self,
        pattern_name: str,
        strategy: str,
        phase: str,
        artefact_type: str = "svg",
        expiry_minutes: int = 60,
    ) -> str:
        """
        Generate a signed URL for a specific artefact.

        Args:
            artefact_type: One of 'svg', 'drawio', 'png'.
            expiry_minutes: URL validity period.
        """
        if not self.bucket:
            return ""

        prefix = self._build_prefix(pattern_name, strategy, phase)
        ext = artefact_type if artefact_type != "drawio" else "drawio"
        blob_path = f"{prefix}.{ext}"

        try:
            import datetime
            blob = self.bucket.blob(blob_path)
            url = blob.generate_signed_url(
                expiration=datetime.timedelta(minutes=expiry_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            logger.error(f"Signed URL generation failed for {blob_path}: {e}")
            return ""

    def list_pattern_diagrams(self, pattern_name: str) -> list:
        """List all diagram blobs for a given pattern."""
        if not self.bucket:
            return []

        prefix = f"patterns/{self._safe_name(pattern_name)}/hadr-diagrams/"
        try:
            blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
            return [b.name for b in blobs]
        except Exception as e:
            logger.error(f"List failed for {prefix}: {e}")
            return []
