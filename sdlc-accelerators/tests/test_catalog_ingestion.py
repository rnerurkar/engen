"""Catalog ingestion: deterministic logic of all three ingesters (Path A).

Modules are loaded by file path (not via sys.path + `src.`) to avoid the cross-service
`src` package collision that occurs when multiple services are imported in one test run.
"""
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "services/catalog-ingestion/src"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Build a synthetic package so the ingesters' relative imports (from .vertex_search_indexer,
# from .config) resolve cleanly and in isolation.
_pkg = types.ModuleType("catalog_ingestion_pkg")
_pkg.__path__ = [str(CI)]
sys.modules["catalog_ingestion_pkg"] = _pkg

_idx = _load("catalog_ingestion_pkg.vertex_search_indexer", CI / "vertex_search_indexer.py")
_cfg = _load("catalog_ingestion_pkg.config", CI / "config.py")
_pat = _load("catalog_ingestion_pkg.ingest_patterns", CI / "ingest_patterns.py")
_skl = _load("catalog_ingestion_pkg.ingest_skills", CI / "ingest_skills.py")
_cards = _load("catalog_ingestion_pkg.register_agent_cards", CI / "register_agent_cards.py")


def test_pattern_discovery_and_docs(tmp_path):
    (tmp_path / "agentic").mkdir()
    for p in ["sequential", "parallel", "loop"]:
        (tmp_path / "agentic" / f"{p}.pdf").write_text("%PDF-1.4")
    pdfs = _pat.discover_pattern_pdfs(str(tmp_path))
    assert len(pdfs) == 3
    docs = _pat.build_documents(pdfs, "bucket")
    assert len(docs) == 3
    assert all(d.doc_id.startswith("pattern-") for d in docs)
    assert _pat.pattern_metadata(pdfs[0])["doc_type"] == "pattern"
    assert [d.doc_id for d in docs] == [d.doc_id for d in _pat.build_documents(pdfs, "bucket")]


def test_skill_frontmatter_and_provenance():
    md = "---\nname: adk-agents\ndescription: Write ADK agents\narchetype: agentic\nversion: 2.1.0\n---\n# body\n"
    fm = _skl.parse_frontmatter(md)
    assert fm["name"] == "adk-agents"
    rec = _skl.to_record("agentic/adk-agents/SKILL.md", md, sha="deadbeef")
    assert rec.sha == "deadbeef" and rec.version == "2.1.0"
    doc = _skl.to_index_document(rec)
    assert doc.struct_data["description"] == "Write ADK agents"
    assert doc.struct_data["sha"] == "deadbeef"
    assert doc.struct_data["doc_type"] == "skill"


def test_agent_card_to_api_hub_registration():
    card1 = {"name": "body-shop-agent", "version": "2.3.0", "url": "https://x/agent-card.json",
             "skills": [{"id": "body-shop-estimate"}], "securitySchemes": {"mtls": {}}}
    r1 = _cards.to_registration(card1)
    assert r1.api_type == "a2a_agent"
    assert r1.capabilities == ["body-shop-estimate"]
    assert r1.auth_method == "mtls"
    card2 = {"name": "rental", "capabilities": ["quote"], "agent_card_url": "https://y", "authentication": "oauth2"}
    r2 = _cards.to_registration(card2)
    assert r2.capabilities == ["quote"] and r2.auth_method == "oauth2"


def test_config_github_url_is_configurable(tmp_path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "project_id: p\nlocation: global\n"
        "vertex_ai_search:\n  pattern_catalog: {data_store_id: a, display_name: A}\n"
        "  skill_catalog: {data_store_id: b, display_name: B}\n"
        "skills:\n  github_repo_url: https://github.com/myorg/my-skills\n"
        "  github_ref: v2\n  skill_glob: '**/SKILL.md'\n"
    )
    cfg = _cfg.IngestionConfig.load(str(cfg_file))
    assert cfg.skills_repo_url == "https://github.com/myorg/my-skills"
    assert cfg.skills_ref == "v2"
