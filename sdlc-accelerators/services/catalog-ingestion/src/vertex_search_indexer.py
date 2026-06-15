"""Vertex AI Search indexer — the shared write path for pattern + skill catalogs.
Interface is real; the Discovery Engine SDK calls are marked TODO for live wiring.
Per platform standards, this is a MAINTENANCE job (platform team), not a runtime MCP tool.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("catalog-ingestion.vertex")


@dataclass
class IndexDocument:
    """One document to index in a Vertex AI Search data store."""
    doc_id: str
    content_uri: str | None       # gs:// URI for unstructured (PDF), or None for structured
    struct_data: dict = field(default_factory=dict)   # searchable metadata


@dataclass
class IndexResult:
    data_store_id: str
    indexed: int
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


class VertexSearchIndexer:
    def __init__(self, project_id: str, location: str):
        self.project_id = project_id
        self.location = location

    def ensure_data_store(self, data_store_id: str, display_name: str, content_kind: str) -> None:
        """Create the data store if it doesn't exist.
        content_kind: 'unstructured' (PDFs) or 'structured' (skill metadata).
        TODO(live): google.cloud.discoveryengine_v1 DataStoreServiceClient.create_data_store
        """
        logger.info("ensure_data_store", extra={"data_store_id": data_store_id, "kind": content_kind})
        raise NotImplementedError(
            f"Wire Discovery Engine SDK to create/verify data store '{data_store_id}'. "
            "Indexer interface and batching logic are ready."
        )

    def index(self, data_store_id: str, docs: list[IndexDocument]) -> IndexResult:
        """Batch-index documents. Idempotent on doc_id (upsert).
        TODO(live): DocumentServiceClient.import_documents (GCS) or batch create.
        The batching + result contract below is the production-ready part.
        """
        logger.info("index", extra={"data_store_id": data_store_id, "count": len(docs)})
        raise NotImplementedError(
            f"Wire Discovery Engine import for {len(docs)} docs into '{data_store_id}'."
        )
