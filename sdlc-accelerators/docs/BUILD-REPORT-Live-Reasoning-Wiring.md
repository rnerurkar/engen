# Build Report — Live Gemini Reasoning Wired (both archetypes)

The single LLM reasoning seam now runs the real Gemini call in both archetypes, with the
human-authored curated prompt bound verbatim. **164 tests passing (+3), clean lint.**

## What was actually stubbed vs already wired

Investigation showed most of the path was already built; the one true stub was the greenfield
pipeline orchestrator.

| Component | Before | After |
|---|---|---|
| `reasoning/llm_provider.py` (greenfield) | Already wired — real `google-genai` call, JSON output, `with_retry`, env-gated `available()` | unchanged |
| `reasoning/llm_harness.py` `invoke_llm_agent` → `_live_invoke` | Already routed to the live provider | unchanged |
| `reasoning/recommend_architecture.py` `run()` | Already wired: validate → retrieve → `invoke_llm_agent` (live) → parse | unchanged |
| `prompts/greenfield-system-prompt.md` | Already a real 38-line curated 8-step prompt | unchanged |
| **`pipeline/orchestrator.py` `run_pipeline`** | **HARD STUB** — called a non-existent `ra.reason()` then unconditionally `raise NotImplementedError`, so `blueprint_start` never reached assembly even with a live model | **WIRED** — calls `RecommendArchitecture.run()` (live Gemini) → `validate_composition` → `assemble_from_selections`; returns `{markdown, json, diagrams}` |
| Brownfield `recommend_architecture.recommend_for_integration` | Already wired — `provider.invoke()` with `BROWNFIELD_RECOMMEND_PROMPT`, confidence gate, graceful degrade | unchanged |

So the fix was surgical: the greenfield `run_pipeline` is the only place that was a hard stub. The
brownfield reasoning path was already fully wired and tested (injected fn, live provider, graceful
degrade — `test_brownfield_recommend.py`).

## How the live call works (both archetypes)

- **Provider:** `reasoning/llm_provider.py` calls Gemini via the `google-genai` SDK. The curated
  system prompt is bound verbatim as `system_instruction`; `response_mime_type=application/json`;
  `temperature=0.2`; wrapped in `with_retry`.
- **Config (env):** `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT` (+ ADC, Vertex AI User
  role, egress to `aiplatform.googleapis.com`), OR `GEMINI_API_KEY` for the direct API.
  `SDLC_LLM_MODEL` overrides the model (default `gemini-2.5-pro`).
- **Graceful behavior:** if the SDK/credentials aren't present, `available()` is False. Greenfield
  raises a clear `NotImplementedError` (surfaced by `blueprint_start` as `reasoning_not_configured`);
  brownfield degrades the affected integration to `requires_review` (never fabricates a confident
  pick).

## Tests
- `tests/test_pipeline_flowthrough.py` (NEW, 3): the pipeline now reaches assembly via the wired
  reasoning path (injected model in CI); composition runs; the live path raises an actionable error
  when unconfigured.
- `tests/test_recommend_architecture.py` (existing): `RecommendArchitecture.run()` with model_fn.
- `brownfield/tests/test_brownfield_recommend.py` (existing): injected fn, live provider
  (`provider.invoke` monkeypatched), graceful degrade.

## Honest residual
No real Gemini call runs in CI (no credentials) — the live leg is exercised via an injected
model / monkeypatched provider. The wiring, prompt binding, JSON contract, retry, and error
handling are all real and tested; only an actual network call to Gemini is out of scope for CI.
The RAG corpus (Pattern Catalog / skill catalog in Vertex AI Search) and the API Hub live call
remain uningested/commented seams, so retrieval degrades to empty candidates until populated —
the model still reasons over spec/plan, just without catalog grounding until the corpus exists.
