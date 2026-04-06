"""
Service HA/DR Ingestion Pipeline
---------------------------------
Ingests service-level HA/DR documentation from SharePoint into a dedicated
Vertex AI Search data store.

Key differences from the pattern ingestion pipeline (vertex_search_pipeline.py):
  1. No component diagram processing — service docs do not contain them.
  2. HA/DR diagrams ARE processed: replaced with LLM-generated text descriptions
     in the chunk content, and the original images are stored in GCS indexed by
     service name + DR strategy + lifecycle phase.
  3. Each chunk carries rich structured metadata (service_name, service_type,
     dr_strategy, lifecycle_phase) to enable precise filtered retrieval.
  4. Chunks are split by DR strategy then by lifecycle phase, not arbitrarily.
"""

import json
import logging
import os
import re
import sys
from typing import Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
import vertexai
from vertexai.generative_models import GenerativeModel, Part

logger = logging.getLogger(__name__)

# ─── Section heading detection ────────────────────────────────────────────

DR_STRATEGY_PATTERNS: Dict[str, List[str]] = {
    "Backup and Restore": [
        r"backup\s*(?:and|&|/)\s*restore",
        r"backup\s*restore",
        r"b(?:ackup)?[/&]r(?:estore)?",
    ],
    "Pilot Light On Demand": [
        r"pilot\s*light\s*on[\s-]*demand",
        r"pilot\s*light\s*\(?\s*on[\s-]*demand\s*\)?",
    ],
    "Pilot Light Cold Standby": [
        r"pilot\s*light\s*(?:\(?cold\s*standby\)?)",
        r"cold\s*standby",
        r"pilot\s*light\s*\(?\s*cold\s*\)?",
    ],
    "Warm Standby": [
        r"warm\s*standby",
    ],
}

LIFECYCLE_PHASE_PATTERNS: Dict[str, List[str]] = {
    "Initial Provisioning": [
        r"initial\s*provisioning",
        r"provisioning",
        r"initial\s*setup",
        r"initial\s*deployment",
    ],
    "Failover": [
        r"failover",
        r"fail[\s-]*over",
        r"during\s*failure",
    ],
    "Failback": [
        r"failback",
        r"fail[\s-]*back",
        r"recovery\s*to\s*primary",
        r"restore\s*to\s*primary",
    ],
}


class ServiceHADRIngestionPipeline:
    """
    Ingests service-level HA/DR documents into Vertex AI Search with
    per-chunk structured metadata.
    """

    def __init__(
        self,
        sp_client,
        project_id: str,
        location: str = "global",
        data_store_id: str = "service-hadr-datastore",
        gcs_bucket_name: str = "engen-service-hadr-images",
    ):
        """
        Args:
            sp_client:        Instance of SharePointClient.
            project_id:       GCP Project ID.
            location:         Vertex AI Search location.
            data_store_id:    Target data store for service HA/DR docs.
            gcs_bucket_name:  Bucket for storing extracted HA/DR diagram images.
        """
        self.sp_client = sp_client
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id

        # GCS
        self.storage_client = storage.Client(project=project_id)
        self.bucket = self.storage_client.bucket(gcs_bucket_name)

        # Vertex AI Search — Document API
        self.doc_client = discoveryengine.DocumentServiceClient()
        self.branch = (
            f"projects/{self.project_id}"
            f"/locations/{self.location}"
            f"/collections/default_collection"
            f"/dataStores/{self.data_store_id}"
            f"/branches/default_branch"
        )

        # Vertex AI — Vision model for diagram descriptions
        vertexai.init(project=project_id, location="us-central1")
        self.vision_model = GenerativeModel("gemini-1.5-flash")

    # ─── Public API ──────────────────────────────────────────────────────

    def run_ingestion(self, service_list: List[Dict[str, Any]]):
        """
        Main entry-point: ingests all services in *service_list*.

        Each entry must contain at a minimum::

            {
                "service_name": "Amazon RDS",
                "service_description": "Managed relational DB service",
                "service_type": "Database",    # Compute|Storage|Database|Network
                "page_url": "https://sharepoint.com/sites/.../SitePages/rds-hadr.aspx"
            }
        """
        logger.info(
            f"Starting service HA/DR ingestion for {len(service_list)} services"
        )
        for svc_meta in service_list:
            try:
                self._process_single_service(svc_meta)
            except Exception as e:
                logger.error(
                    f"Failed to process service '{svc_meta.get('service_name')}': {e}",
                    exc_info=True,
                )

    def _process_single_service(self, svc_meta: Dict[str, Any]):
        svc_name = svc_meta["service_name"]
        logger.info(f"Processing service: {svc_name}")

        # 1. Fetch raw HTML from SharePoint
        raw_html = self.sp_client.fetch_page_html(svc_meta["page_url"])
        if not raw_html:
            logger.warning(f"No HTML content for {svc_name}")
            return

        # 2. Extract text and handle images
        plain_text, image_descriptions, diagram_records = (
            self._extract_text_and_process_images(raw_html, svc_name)
        )

        # 3. Prepend diagram descriptions into the text
        if image_descriptions:
            desc_block = "\n".join(image_descriptions) + "\n\n"
            plain_text = desc_block + plain_text

        # 4. Chunk by DR strategy → lifecycle phase → size
        chunks = self._chunk_document(plain_text, svc_meta, diagram_records)

        # 5. Index chunks in Vertex AI Search
        self._index_chunks(chunks)

        logger.info(
            f"Finished {svc_name}: {len(chunks)} chunks indexed"
        )

    # ─── Image handling ──────────────────────────────────────────────────

    def _extract_text_and_process_images(
        self, html_content: str, service_name: str
    ) -> Tuple[str, List[str], List[Dict[str, Any]]]:
        """
        Extracts plain text from HTML.  For any <img> found, downloads it,
        generates an LLM description, stores the image in GCS, and replaces
        the image in the text with the description.

        Returns:
            plain_text:       The full text content with diagrams replaced.
            descriptions:     List of summary strings for each diagram.
            diagram_records:  List of dicts, each with ``gcs_url``,
                              ``description``, and ``diagram_index`` so the
                              chunker can attach them to the correct chunks.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        descriptions: List[str] = []
        diagram_records: List[Dict[str, Any]] = []

        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", service_name)

        for idx, img_tag in enumerate(soup.find_all("img")):
            original_src = img_tag.get("src")
            if not original_src:
                continue

            # Download image bytes
            try:
                image_bytes = self.sp_client.download_image(original_src)
                if not image_bytes:
                    continue
            except Exception as e:
                logger.warning(f"Image download failed ({original_src}): {e}")
                continue

            # Generate description with Gemini Vision
            alt_text = img_tag.get("alt", "HA/DR diagram")
            description = self._describe_diagram(image_bytes, alt_text)
            descriptions.append(
                f"[DIAGRAM {idx + 1}: {alt_text}] {description}"
            )

            # Upload image to GCS
            gcs_path = f"services/{safe_name}/hadr-diagrams/diagram_{idx}.png"
            gcs_url = ""
            try:
                blob = self.bucket.blob(gcs_path)
                blob.upload_from_string(image_bytes, content_type="image/png")
                gcs_url = f"gs://{self.bucket.name}/{gcs_path}"
            except Exception as e:
                logger.warning(f"GCS upload failed for {gcs_path}: {e}")

            # Record diagram metadata for later attachment to chunks
            diagram_records.append({
                "diagram_index": idx,
                "gcs_url": gcs_url,
                "description": description,
            })

            # Replace <img> tag with a marked paragraph so we can trace
            # which diagram ended up in which section during chunking.
            # The marker tag carries a data attribute with the diagram index.
            replacement = soup.new_tag("p")
            replacement["data-diagram-idx"] = str(idx)
            replacement.string = f"[DIAGRAM {idx}: {description}]"
            img_tag.replace_with(replacement)

        plain_text = soup.get_text(separator="\n", strip=True)
        return plain_text, descriptions, diagram_records

    def _describe_diagram(self, image_bytes: bytes, alt_text: str) -> str:
        """Use Gemini Vision to describe an HA/DR diagram."""
        prompt = (
            "Analyse this HA/DR architecture diagram.  "
            "Describe the infrastructure components, their redundancy setup, "
            "replication flows, and failover mechanisms.  "
            "Be concise but technically precise."
        )
        try:
            image_part = Part.from_data(data=image_bytes, mime_type="image/png")
            response = self.vision_model.generate_content(
                [prompt, image_part],
                generation_config={"max_output_tokens": 512, "temperature": 0.2},
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Diagram description failed: {e}")
            return alt_text

    # ─── Chunking ────────────────────────────────────────────────────────

    def _chunk_document(
        self,
        content: str,
        svc_meta: Dict[str, str],
        diagram_records: Optional[List[Dict[str, Any]]] = None,
        max_chunk_words: int = 1500,
        overlap_words: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Splits content hierarchically:
          1. By DR strategy heading
          2. By lifecycle phase heading
          3. By word-count window

        Each chunk carries full structured metadata so retrieval can filter
        precisely.  If *diagram_records* is supplied, any diagrams whose
        ``[DIAGRAM N: …]`` marker text appears inside a chunk's text are
        attached to that chunk's ``struct_data`` as ``diagram_gcs_urls``
        and ``diagram_descriptions``.
        """
        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0

        # Build a quick lookup from marker text prefix → diagram record
        # The marker format inserted by _extract_text_and_process_images is:
        #   [DIAGRAM <idx>: <description>]
        _diagram_lookup = {}
        for rec in (diagram_records or []):
            marker_prefix = f"[DIAGRAM {rec['diagram_index']}:"
            _diagram_lookup[marker_prefix] = rec

        strategy_sections = self._split_by_heading(
            content, DR_STRATEGY_PATTERNS
        )

        for strategy, strategy_text in strategy_sections.items():
            phase_sections = self._split_by_heading(
                strategy_text, LIFECYCLE_PHASE_PATTERNS
            )

            for phase, phase_text in phase_sections.items():
                for text_chunk in self._window_chunk(
                    phase_text, max_chunk_words, overlap_words
                ):
                    # Determine which diagrams fall inside this chunk
                    chunk_diagram_urls: List[str] = []
                    chunk_diagram_descs: List[str] = []
                    for marker_prefix, rec in _diagram_lookup.items():
                        if marker_prefix in text_chunk:
                            if rec.get("gcs_url"):
                                chunk_diagram_urls.append(rec["gcs_url"])
                            if rec.get("description"):
                                chunk_diagram_descs.append(rec["description"])

                    doc_id = (
                        re.sub(r"[^a-zA-Z0-9_-]", "_", svc_meta["service_name"])
                        + f"_{chunk_idx}"
                    )

                    struct_data = {
                        "service_name": svc_meta["service_name"],
                        "service_description": svc_meta.get(
                            "service_description", ""
                        ),
                        "service_type": svc_meta.get(
                            "service_type", ""
                        ),
                        "dr_strategy": strategy,
                        "lifecycle_phase": phase,
                        "chunk_index": chunk_idx,
                        "diagram_gcs_urls": chunk_diagram_urls,
                        "diagram_descriptions": chunk_diagram_descs,
                    }

                    chunks.append(
                        {
                            "id": doc_id,
                            "content": text_chunk,
                            "struct_data": struct_data,
                        }
                    )
                    chunk_idx += 1

        total_diags = sum(
            len(c["struct_data"].get("diagram_gcs_urls", []))
            for c in chunks
        )
        logger.info(
            f"Chunked '{svc_meta['service_name']}' into {len(chunks)} chunks "
            f"({total_diags} diagram references attached)"
        )
        return chunks

    # ─── Heading-based splitting helpers ─────────────────────────────────

    @staticmethod
    def _detect_category(
        line: str, patterns: Dict[str, List[str]]
    ) -> Optional[str]:
        """Check whether *line* matches any of the heading patterns."""
        line_lower = line.lower()
        for category, regexes in patterns.items():
            for regex in regexes:
                if re.search(regex, line_lower):
                    return category
        return None

    def _split_by_heading(
        self, content: str, patterns: Dict[str, List[str]]
    ) -> Dict[str, str]:
        """
        Split *content* into named sections using *patterns* for heading
        detection.  Lines before the first recognised heading are stored
        under the key ``"general"``.
        """
        sections: Dict[str, List[str]] = {}
        current_key = "general"
        sections[current_key] = []

        for line in content.split("\n"):
            detected = self._detect_category(line, patterns)
            if detected:
                current_key = detected
                if current_key not in sections:
                    sections[current_key] = []
                sections[current_key].append(line)
            else:
                sections[current_key].append(line)

        return {k: "\n".join(v) for k, v in sections.items() if v}

    @staticmethod
    def _window_chunk(
        text: str, max_words: int, overlap: int
    ) -> List[str]:
        """Sliding-window word-level chunker."""
        words = text.split()
        if not words:
            return [text] if text.strip() else []
        chunks: List[str] = []
        start = 0
        while start < len(words):
            end = start + max_words
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            start += max_words - overlap
        return chunks if chunks else [text]

    # ─── Vertex AI Search indexing ───────────────────────────────────────

    def _index_chunks(self, chunks: List[Dict[str, Any]]):
        """Upsert each chunk as a Document in Vertex AI Search."""
        for chunk in chunks:
            try:
                document = discoveryengine.Document(
                    id=chunk["id"],
                    struct_data=chunk["struct_data"],
                    content=discoveryengine.Document.Content(
                        raw_bytes=chunk["content"].encode("utf-8"),
                        mime_type="text/plain",
                    ),
                )
                request = discoveryengine.CreateDocumentRequest(
                    parent=self.branch,
                    document=document,
                    document_id=chunk["id"],
                )
                self.doc_client.create_document(request=request)
            except Exception as e:
                logger.error(f"Failed to index chunk {chunk['id']}: {e}")


# ─── CLI entry-point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    current_file_path = os.path.abspath(__file__)
    pipeline_dir = os.path.dirname(current_file_path)
    service_root = os.path.dirname(pipeline_dir)
    if service_root not in sys.path:
        sys.path.append(service_root)

    from config import Config as IngestionConfig
    from clients.sharepoint import SharePointClient

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        config = IngestionConfig()
        sp_client = SharePointClient(config)

        pipeline = ServiceHADRIngestionPipeline(
            sp_client=sp_client,
            project_id=config.PROJECT_ID,
            location=config.LOCATION,
            data_store_id=os.getenv(
                "SERVICE_HADR_DS_ID", "service-hadr-datastore"
            ),
            gcs_bucket_name=os.getenv(
                "SERVICE_HADR_GCS_BUCKET", "engen-service-hadr-images"
            ),
        )

        # The service list would come from a SharePoint list or a JSON file.
        # For now we load from an env-referenced JSON file on GCS or local disk.
        svc_list_path = os.getenv("SERVICE_HADR_LIST", "service_catalog.json")
        if os.path.isfile(svc_list_path):
            with open(svc_list_path, "r", encoding="utf-8") as f:
                service_list = json.load(f)
        else:
            logger.error(f"Service list not found at {svc_list_path}")
            sys.exit(1)

        pipeline.run_ingestion(service_list)

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
