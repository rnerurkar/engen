# Build Report — Live LLM Reasoning Wired (recommend_architecture, both archetypes)

The `recommend_architecture` reasoning seam is now WIRED active code (not commented out) in both
greenfield and brownfield. **129 tests passing (+11), clean lint.**

## Greenfield (Solution Accelerator)
- New `services/solution-accelerator/src/reasoning/llm_provider.py`: a real Gemini provider via
  google-genai. `available()` gates on SDK + credentials; `invoke()` builds the client (Vertex AI
  backend via GOOGLE_CLOUD_PROJECT+ADC, or direct GEMINI_API_KEY), binds the **authored prompt
  verbatim** as system_instruction, requests `response_mime_type=application/json`, low temperature,
  and wraps in with_retry.
- `reasoning/llm_harness.py` `_live_invoke` now routes to the provider (was a commented-out block).
  When unconfigured it raises a clear, actionable error; tests inject `model_fn`.

## Brownfield (Tool 2)
- New `brownfield/src/brownfield/recommend_architecture.py`: reuses the same Gemini provider, binds
  the authored brownfield migration prompt verbatim, and applies the documented **confidence < 0.65
  → requires_review** threshold. The pipeline routes through it by default (no recommend_fn needed);
  degrades to `requires_review` when the provider is unconfigured (never fabricates a confident pick).

## Configuration (to actually reason)
- Vertex AI backend: `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, ADC (Vertex AI User),
  egress to aiplatform.googleapis.com. OR direct: `GEMINI_API_KEY`.
- `SDLC_LLM_MODEL` overrides the model (default gemini-2.5-pro).

## Tested (mocked SDK — no real credentials needed in CI)
- availability gating (false without creds, true with Vertex project)
- live invoke builds client, binds prompt verbatim, requests JSON, parses the dict
- harness routes to provider when configured; raises actionable error when not
- brownfield: injected fn precedence; live selection with confidence; <0.65 → review;
  prompt bound verbatim; full pipeline routes through live reasoning by default

## What remains (honest)
- **Pattern Catalog corpus + retrieval** (the candidates the LLM chooses among) is still the RAG
  seam / unbuilt content — the LLM reasons over whatever candidates retrieval returns.
- The **reasoning prompt content** is human-authored (greenfield: prompts/greenfield-system-prompt.md;
  brownfield: BROWNFIELD_RECOMMEND_PROMPT) — bound verbatim, not invented here.
- No real Gemini call runs in CI (no credentials); the wiring is proven via a mocked client.
