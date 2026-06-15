# Build Report — Live-Service Seams (the "API Hub treatment" applied platform-wide)

Every live-service boundary now follows the same pattern: real interface + query/result shaping,
an injectable test seam, the actual SDK/network call **written but commented out**, and a concrete
wiring checklist. **92 tests passing (6 new seam tests), clean lint.**

## The pattern
For each boundary: inject a fake in tests (proven working); the live call sits commented out in a
`_live_*` method with a numbered checklist; when not wired it raises `NotImplementedError` directly
(NOT through with_retry — a not-wired seam is not a transient failure). The checklist always covers:
pip install, credentials/role, network egress, and "wrap in with_retry on uncomment".

## Boundaries treated
| Boundary | File | Live call (commented) | Seam |
|---|---|---|---|
| Apigee API Hub | `clients/apigee_hub.py` | `apihub_v1.list_apis(filter=...)` | `_search` |
| Vertex AI Search | `clients/vertex_search.py` | `discoveryengine_v1.SearchServiceClient.search` | `_search` |
| Eraser MCP server | `clients/eraser_mcp.py` | MCP `streamablehttp_client` + `call_tool("render")` | `_render` |
| AlloyDB | `clients/alloydb_taskstore.py` | alloydb connector + sqlalchemy; `SCHEMA_DDL` (3 tables) + RLS | `_execute` |
| GCS | `clients/gcs_client.py` (+ GG copy) | `storage.Client().blob.upload_from_string` / `download_as_bytes` | `_put`/`_get` |
| Gemini (ADK LlmAgent) | `reasoning/llm_harness.py` | `LlmAgent(...) + InMemoryRunner.run`, JSON output | `model_fn` |

## Notes added per request
- **discover_integrations**: the honest taxonomy-tuning note is now an inline comment on
  `_capability_terms` — the slugify heuristic matches the FNOL example but must be tuned against
  real registered capability names (a slug mismatch silently hides a registered agent/tool).
- **apigee_hub `_live_search`**: full wiring checklist — `pip install google-cloud-apihub`,
  project_id + api_hub_instance, ADC credentials (API Hub Viewer), egress to apihub.googleapis.com,
  uncomment + wrap in with_retry.
- **llm_harness `_live_invoke`**: note that the system_prompt is authored IP — bind verbatim as
  the agent instruction, do not inline/mutate.

## Graceful degradation
`recommend_architecture.retrieve()` guards both the Vertex AI Search and API Hub calls: until the
live calls are uncommented (and the corpus ingested) it degrades to empty results so the pipeline
orchestration stays testable end-to-end.

## Validations (tested — test_live_service_seams.py)
- ✅ Each boundary: injected seam returns shaped results
- ✅ Each boundary: unwired live path raises NotImplementedError (no fabrication)
- ✅ AlloyDB SCHEMA_DDL has the 3 expected tables; GCS reference backing round-trips
