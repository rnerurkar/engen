"""Ingest skill metadata from the GitHub skills repo into the Vertex AI Search Skill Catalog.

Source of truth = GitHub (configurable repo URL). Search index = Vertex AI Search.
The ingester reads each SKILL.md's YAML frontmatter (name, description, archetype, version)
plus the file's git SHA for provenance, embeds the description, and indexes the metadata.

Skills are searched via search_skills() (RAG) at reasoning time — NOT read from GitHub
per request. This job bridges source (GitHub) -> discovery index (Vertex AI Search).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .config import IngestionConfig
from .vertex_search_indexer import IndexDocument, VertexSearchIndexer

logger = logging.getLogger("catalog-ingestion.skills")


@dataclass
class SkillRecord:
    skill_id: str
    name: str
    description: str
    archetype: str
    version: str
    sha: str
    path: str


def parse_frontmatter(skill_md: str) -> dict:
    """Parse the YAML frontmatter block (--- ... ---) at the top of a SKILL.md."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", skill_md, re.DOTALL)
    if not m:
        return {}
    import yaml
    return yaml.safe_load(m.group(1)) or {}


def to_record(path: str, skill_md: str, sha: str) -> SkillRecord:
    """Build a SkillRecord from a SKILL.md's frontmatter + provenance."""
    fm = parse_frontmatter(skill_md)
    name = fm.get("name") or path.split("/")[-2] if "/" in path else path
    return SkillRecord(
        skill_id="skill-" + re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-"),
        name=str(name),
        description=str(fm.get("description", "")),
        archetype=str(fm.get("archetype", "shared")),
        version=str(fm.get("version", "1.0")),
        sha=sha,
        path=path,
    )


def to_index_document(rec: SkillRecord) -> IndexDocument:
    """Skill metadata is structured; description is the embedded/searchable field."""
    return IndexDocument(
        doc_id=rec.skill_id,
        content_uri=None,
        struct_data={
            "name": rec.name,
            "description": rec.description,   # semantic search target
            "archetype": rec.archetype,
            "version": rec.version,
            "sha": rec.sha,                   # provenance (system prompt requires SHA+version)
            "path": rec.path,
            "doc_type": "skill",
        },
    )


def fetch_skill_files(repo_url: str, ref: str, skill_glob: str) -> list[tuple[str, str, str]]:
    """Return [(path, content, sha)] for each SKILL.md in the configurable repo.
    TODO(live): use the GitHub API (or GitHub MCP read_file) against repo_url@ref.
    Kept as a separate function so the parsing/indexing logic is testable offline."""
    raise NotImplementedError(
        f"Wire GitHub fetch of '{skill_glob}' from {repo_url}@{ref} "
        "(GitHub REST API or GitHub MCP read_file). Parsing + indexing logic is ready."
    )


def run(config_path: str | None = None) -> dict:
    """Entry point: ingest skill metadata from the configurable GitHub repo."""
    cfg = IngestionConfig.load(config_path)
    store = cfg.store("skill_catalog")
    logger.info("skills_repo", extra={"repo": cfg.skills_repo_url, "ref": cfg.skills_ref})

    files = fetch_skill_files(cfg.skills_repo_url, cfg.skills_ref, cfg.raw["skills"]["skill_glob"])
    records = [to_record(p, c, s) for p, c, s in files]
    docs = [to_index_document(r) for r in records]

    indexer = VertexSearchIndexer(cfg.project_id, cfg.location)
    indexer.ensure_data_store(store["data_store_id"], store["display_name"], "structured")
    indexer.index(store["data_store_id"], docs)
    return {"skills": len(records), "repo": cfg.skills_repo_url}
