"""Ingest pattern documentation PDFs into the Vertex AI Search Pattern Catalog.

Flow: discover local PDFs -> stage to GCS -> build IndexDocuments with metadata
-> index into the Pattern Catalog data store. The discovery + metadata + doc-building
logic is real and tested; GCS upload and indexing are wired through the indexer (TODO live).
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from .config import IngestionConfig
from .vertex_search_indexer import IndexDocument, VertexSearchIndexer

logger = logging.getLogger("catalog-ingestion.patterns")


def discover_pattern_pdfs(source_dir: str) -> list[Path]:
    """Find all pattern PDFs in the workspace folder (sorted for determinism)."""
    root = Path(source_dir)
    if not root.exists():
        raise FileNotFoundError(f"Pattern source dir not found: {source_dir}")
    return sorted(root.rglob("*.pdf"))


def pattern_metadata(pdf: Path) -> dict:
    """Derive searchable metadata from the file. Convention: parent dir = archetype,
    filename stem = pattern name. (e.g. agentic/sequential-pipeline.pdf)"""
    archetype = pdf.parent.name if pdf.parent.name not in (".", "patterns") else "agentic"
    pattern_name = pdf.stem.replace("-", " ").replace("_", " ").title()
    return {
        "pattern_name": pattern_name,
        "archetype": archetype,
        "source_filename": pdf.name,
        "doc_type": "pattern",
    }


def build_documents(pdfs: list[Path], staging_bucket: str) -> list[IndexDocument]:
    """Build one IndexDocument per pattern PDF. content_uri points at the staged GCS object."""
    docs = []
    for pdf in pdfs:
        doc_id = "pattern-" + hashlib.sha256(pdf.name.encode()).hexdigest()[:16]
        gcs_uri = f"gs://{staging_bucket}/patterns/{pdf.name}"
        docs.append(IndexDocument(doc_id=doc_id, content_uri=gcs_uri, struct_data=pattern_metadata(pdf)))
    return docs


def stage_to_gcs(pdfs: list[Path], staging_bucket: str) -> None:
    """Upload PDFs to the GCS staging bucket Vertex AI Search imports from.
    TODO(live): google.cloud.storage upload_from_filename."""
    raise NotImplementedError(f"Wire GCS upload of {len(pdfs)} PDFs to gs://{staging_bucket}/patterns/")


def run(config_path: str | None = None) -> dict:
    """Entry point: ingest all pattern PDFs into the Pattern Catalog data store."""
    cfg = IngestionConfig.load(config_path)
    source_dir = cfg.raw["patterns"]["source_dir"]
    bucket = cfg.raw["patterns"]["staging_gcs_bucket"]
    store = cfg.store("pattern_catalog")

    pdfs = discover_pattern_pdfs(source_dir)
    docs = build_documents(pdfs, bucket)
    logger.info("patterns_discovered", extra={"count": len(pdfs)})

    # Live path (raises until wired):
    indexer = VertexSearchIndexer(cfg.project_id, cfg.location)
    indexer.ensure_data_store(store["data_store_id"], store["display_name"], "unstructured")
    stage_to_gcs(pdfs, bucket)
    indexer.index(store["data_store_id"], docs)
    return {"discovered": len(pdfs), "documents": len(docs)}
