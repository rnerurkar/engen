# Catalog Sources (local ingestion inputs)

Place ingestion inputs here, then run the catalog-ingestion CLI (platform-team job).

- `patterns/` — the 70 pattern documentation **PDFs** (organized by archetype subfolder,
  e.g. `patterns/agentic/sequential-pipeline.pdf`). Ingested into Vertex AI Search.
- `agent-cards/` — the 50+ third-party **agent-card JSON** files. Registered in Apigee API Hub.

Skills are NOT here — they live in the configurable GitHub skills repo
(`services/catalog-ingestion/config/ingestion-config.yaml` → `skills.github_repo_url`)
and are ingested into Vertex AI Search directly from there.
