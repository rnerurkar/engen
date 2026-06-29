"""Tool 2 — recommend_architecture: the one LLM reasoning stage in the brownfield pipeline.

Per integration: build a query from the integration's intent + functional_category + target_tech,
retrieve candidate patterns (RAG seam), and have the LLM pick a winner with a confidence. This is
the WIRED live reasoning path (via the shared Gemini provider), with graceful fallbacks:
  - an injected recommend_fn (tests / custom) takes precedence, else
  - the live LLM provider when configured, else
  - degrade to requires_review (never fabricate a confident selection).

The reasoning PROMPT is human-authored content (loaded from a prompt file); this module binds it
verbatim. Pattern CANDIDATES come from the Pattern Catalog (Vertex AI Search) — that retrieval is
the RAG seam, shared with the platform's vertex_search client.
"""

from __future__ import annotations

import json
import os
from typing import Any, cast

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _load_provider() -> Any:
    """Lazily import and return the platform's shared live Gemini provider.

    Uses the centralized cross-service path bootstrap (_srcpaths) rather than an ad-hoc insert."""
    import sys

    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    import _srcpaths

    _srcpaths.ensure("solution-accelerator")
    from reasoning import llm_provider

    return llm_provider


BROWNFIELD_RECOMMEND_PROMPT = (
    "You are a brownfield migration architect. Given one integration's migration intent, its "
    "functional categories, the chosen target technology, and a list of candidate transition "
    "patterns retrieved from the Pattern Catalog, select the single best pattern. Respond ONLY as "
    'JSON: {"pattern_ref": <id>, "confidence": <0..1>, "rationale": <short>}. Confidence is '
    "your calibrated certainty based on how well the top candidate fits versus the runner-up. "
    "If no candidate fits well, return the best with confidence < 0.65 so it is flagged for review."
)


def _build_user_message(substitution: dict[str, Any], candidates: list[Any]) -> str:
    """Serialize the integration + candidate patterns into the LLM user message (JSON)."""
    return json.dumps(
        {
            "integration_id": substitution.get("integration_id"),
            "r_factor": substitution.get("r_factor"),
            "target_tokens": substitution.get("target_tokens", []),
            "transition_pattern_ref": substitution.get("transition_pattern_ref"),
            "candidate_patterns": candidates,
        }
    )


def recommend_for_integration(
    substitution: dict[str, Any],
    candidates: list[Any] | None = None,
    recommend_fn: Any = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """Select a transition pattern for one integration. Returns
    {pattern_ref, confidence, requires_review, rationale?}."""
    candidates = candidates or []
    if recommend_fn is not None:
        return cast("dict[str, Any]", recommend_fn(substitution))

    provider = _load_provider()
    ok, _reason = provider.available()
    if not ok:
        # Degrade gracefully — never fabricate a confident pick.
        return {
            "pattern_ref": substitution.get("transition_pattern_ref", "n/a"),
            "confidence": 0.0,
            "requires_review": True,
        }

    sel = provider.invoke(
        prompt or BROWNFIELD_RECOMMEND_PROMPT,
        _build_user_message(substitution, candidates),
    )
    confidence = float(sel.get("confidence", 0.0))
    return {
        "pattern_ref": sel.get(
            "pattern_ref", substitution.get("transition_pattern_ref", "n/a")
        ),
        "confidence": confidence,
        "requires_review": confidence < 0.65,  # documented threshold
        "rationale": sel.get("rationale", ""),
    }
