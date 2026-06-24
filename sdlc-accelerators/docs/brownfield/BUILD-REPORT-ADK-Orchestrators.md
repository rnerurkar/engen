# Build Report — ADK SequentialAgent Orchestrators (both archetypes)

Exposed each archetype's tested pipeline as an ADK **SequentialAgent** with a single reasoning
**LlmAgent** sub-agent and deterministic steps for everything else. Agent names are distinct across
archetypes. **148 tests passing (+9), clean lint.**

## The design (the safe version)
Per the architecture's load-bearing constraints, only the ONE reasoning stage is an LlmAgent;
substitution, ADR compliance, and assembly stay deterministic. Assembly CALLS the Eraser MCP tool
to render diagrams (tool use), but no LLM authors the blueprint/contract.

### Greenfield
- SequentialAgent: **`greenfield_blueprint_orchestrator`**
- Sub-agents: `greenfield_validate_spec` (det.) → **`greenfield_architecture_recommender`** (LlmAgent)
  → `greenfield_assemble_blueprint` (det. + Eraser MCP tool)
- `services/solution-accelerator/src/reasoning/blueprint_orchestrator.py` + `adk_steps.py`

### Brownfield
- SequentialAgent: **`brownfield_migration_orchestrator`**
- Sub-agents: `brownfield_migration_readiness` (det.) → `brownfield_substitution` (det., NO LLM)
  → **`brownfield_pattern_recommender`** (LlmAgent) → `brownfield_adr_compliance` (det. gate,
  preserved as its own step) → `brownfield_assemble_contract` (det. + Eraser MCP tool)
- `brownfield/src/brownfield/orchestrator/migration_orchestrator.py` + `adk_steps.py`

**Distinct names:** the greenfield and brownfield agent-name sets are disjoint (tested).

## Why not "two agents, second assembles with an LLM"
The original proposal would have (a) put an LLM in `assemble_blueprint` — breaking the documented
"all assembly is deterministic — no LLM" reproducibility/safety property — and (b) collapsed the
deterministic ADR compliance gate. Both are preserved here: ADR compliance is its own step, and
assembly is deterministic (it only calls the Eraser MCP tool).

## Integration
- ADK is import-guarded: `available()` reports usability; `build_orchestrator()` constructs the
  real agents when google-adk is installed (it is, ADK 2.2.0). The orchestrators wrap the existing
  tested pipeline functions — the pipeline contract is unchanged.
- Brownfield server: opt-in flag `_USE_ADK_ORCHESTRATOR` (off by default — the tested pipeline runs
  directly; when on + ADK present, blueprint_start drives the SequentialAgent).
- IP boundary respected: SequentialAgent composition is plain ADK; NO meta-skills / STL / signed
  Design Contracts are introduced.

## Honest notes
- **ADK 2.2.0 deprecates `SequentialAgent`** in favor of `Workflow`, but `Workflow` is not importable
  from `google.adk.agents` in 2.2.0 — so `SequentialAgent` is the correct working API today. When a
  release ships `Workflow`, swap the two `SequentialAgent(...)` constructions (one per archetype).
  The deprecation warning is filtered in pyproject to keep CI output clean.
- The deterministic ADK steps wrap the tested pipeline functions and emit ADK events; the heavy
  end-to-end ADK run (InMemoryRunner driving the full SequentialAgent with a live model) is not
  exercised in CI (no credentials) — structure, names, and the deterministic/LLM split are tested.

---

## Update — Pattern retrieval wired as an ADK FunctionTool (recommender only)

The one place tool-calling belongs is now wired: each recommender LlmAgent has a pattern-retrieval
tool it controls at reasoning time. The deterministic gating/transform steps deliberately have NO
tools — preserving the fixed-order governance guarantee.

- **Greenfield:** `reasoning/pattern_search_tool.py` → `search_architecture_patterns(ordering_signals)`
  attached to `greenfield_architecture_recommender`.
- **Brownfield:** `orchestrator/pattern_search_tool.py` → `search_transition_patterns(target_tech,
  functional_categories, r_factor)` attached to `brownfield_pattern_recommender`.

Both wrap the existing `VertexSearchClient` seam (Pattern Catalog over Vertex AI Search), are
injectable for tests, and degrade to an empty candidate list when the corpus/live call isn't
configured (no crash). Retrieval only — the tool returns candidates; the LlmAgent still selects and
justifies, and (brownfield) flags low-confidence picks for review.

**Governance guarantee, tested:** `test_deterministic_steps_have_no_tools` /
`test_brownfield_deterministic_steps_have_no_tools` assert that validate/substitution/ADR/assembly
carry no tools — so the fixed order and the ADR gate stay structural, not LLM-discretionary. **154
tests passing.**

### Why only this step is a tool
Making substitution or ADR-compliance into tools would hand the LLM discretion over whether/when
they run — but the architecture mandates "four tools run in a fixed order" and "no LLM fallback" for
substitution, and the ADR gate must run independent of the agent that wants its pattern approved.
Pattern *retrieval* is the opposite: it IS reasoning-time work the recommender should drive. So
retrieval becomes a tool; gating/transform stay sequential steps.
