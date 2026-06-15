# Catalog Ingestion (platform-team maintenance pipeline)

Populates the discovery surfaces the Solution Accelerator's `recommend_architecture`
searches. This is a **maintenance job run by the platform team** (the "~10 hrs/quarter
catalog maintenance" line item) — NOT a runtime tool on the Solution Accelerator MCP server.

## Three ingesters, three architecturally-correct planes

| Source | Target | Discovered at runtime by |
|---|---|---|
| 70 pattern **PDFs** (local) | **Vertex AI Search** — Pattern Catalog data store | `search_patterns()` (RAG) |
| 100+ **skills** (GitHub repo, configurable URL) | **Vertex AI Search** — Skill Catalog data store | `search_skills()` (RAG) |
| 50+ **agent cards** (local JSON) | **Apigee API Hub** (`type=a2a_agent`) | `discover_integrations()` (API Hub query) |

**Why agent cards go to API Hub, not Vertex AI Search:** the architecture designates
Apigee API Hub as the single discovery surface for MCP servers + A2A agents + REST APIs,
and the source of truth for all tool/agent registrations. There are exactly 2 Vertex AI
Search data stores (patterns, skills). Agent discovery is a structured API Hub query
(`type=a2a_agent, capabilities CONTAINS '...'`), not semantic search over embedded cards.

**Why skills go to Vertex AI Search, not GitHub-MCP-at-runtime:** `search_skills()` is a
RAG tool (semantic match needs embeddings; the system prompt requires SHA+version
provenance; the latency budget rules out walking a repo per request). GitHub is the
**source** of skill content; Vertex AI Search is the **discovery index**. This job bridges
them. (The GitHub MCP Server has a different role — the coding agent reads Terraform module
interfaces through it at generation time.)

## Configuration

All environment-specific values live in `config/ingestion-config.yaml`. The **GitHub skills
repo URL is configurable** there (`skills.github_repo_url`) — change per company/fork without
touching code. If you use a machine-readable skill manifest instead of SKILL.md frontmatter,
set `skills.manifest_path`.

## Usage

```bash
python -m catalog_ingestion.cli patterns       # PDFs -> Pattern Catalog
python -m catalog_ingestion.cli skills          # GitHub repo -> Skill Catalog
python -m catalog_ingestion.cli agent-cards     # JSON -> Apigee API Hub
python -m catalog_ingestion.cli all
```

## Build status

Deterministic logic (discovery, metadata extraction, frontmatter parsing, card mapping,
registration-payload building, config) is real and tested. The external calls — GCS upload,
Discovery Engine indexing, GitHub fetch, Apigee API Hub create_api — are wired through clean
interfaces and marked `TODO(live)`. Provide credentials + the SDKs to activate.
