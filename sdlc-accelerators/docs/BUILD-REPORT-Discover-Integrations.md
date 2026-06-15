# Build Report — discover_integrations (real logic + commented-out live call)

Replaced the near-empty stub with real query construction, response shaping, and the
documented A2A>MCP>Build priority. Wrote the actual Apigee API Hub network call, commented out.
**86 tests passing (9 new), clean lint.**

## What's now real and tested (#2)
- `clients/apigee_hub.py` — `ApigeeHubClient`:
  - `build_filter(type, capabilities, lifecycle)` constructs the API Hub filter matching the
    documented FNOL example (`type=a2a_agent, capabilities CONTAINS 'body-shop-estimate'`).
  - `search(...)` runs the query and `_to_entry` shapes raw records into `ApiHubEntry`
    (endpoint, auth, capabilities, Agent Card URL, lifecycle, version) per arch doc line 373.
  - `_search` injection seam for tests.
- `reasoning/discover_integrations.py`:
  - Derives capability search terms from data sources / partners (slugify).
  - Partners flagged "operate their own system" → A2A query; data sources → MCP + REST queries.
  - De-dups by api_id; applies the **A2A (reuse) > MCP (existing) > Build (new)** priority →
    `recommendation: prefer_a2a | prefer_mcp | build_new`.
  - Wired into `recommend_architecture.retrieve()` (degrades gracefully until the live call is wired).

## The live call (#1) — written, commented out
`ApigeeHubClient._live_search` contains the real `google-cloud-apihub` call
(`apihub_v1.ApiHubClient().list_apis(filter=...)`, attribute extraction, result shaping),
COMMENTED OUT. Until uncommented it raises `NotImplementedError` directly (not retried — it
is not a transient failure). To wire: uncomment, `pip install google-cloud-apihub`, supply
project_id + api_hub_instance + ADC credentials, ensure egress to apihub.googleapis.com, and
wrap the list_apis call in `with_retry(...)` (noted inline).

## Validations (tested)
- ✅ Filter construction matches the documented shape
- ✅ Discovers A2A agent with capabilities, auth, Agent Card URL, version (FNOL body-shop)
- ✅ Discovers MCP servers; REST APIs path exercised
- ✅ Priority: prefer_a2a / prefer_mcp / build_new
- ✅ De-dup across capability terms
- ✅ Live call raises NotImplementedError when not wired (no fabrication)
