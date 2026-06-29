"""Phase A — agentic shaping (the ONE LlmAgent → Epic Signal Ledger).

Reuses the SAME LlmAgent harness as recommend_architecture (reasoning.llm_harness.invoke_llm_agent) for
a second, bounded, EXTRACTIVE pass. The agent emits section-keyed signals; a DETERMINISTIC validator then:
  - keeps only the 10 known section buckets,
  - drops any signal whose `epic_span` is not a verbatim substring of the Epic (this is how the agent
    'cannot fabricate/alter' — spans not in the Epic, or values not grounded in their span, are removed),
  - normalizes/repairs shape.

The agent does NOT map sections to a spec and does NOT assign confidence — those are Phase B (deterministic).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ingest.epic_models import (
    VALID_SECTION_NUMS,
    Epic,
    EpicProvenance,
    EpicSignalLedger,
    LedgerSection,
    LedgerSignal,
    empty_ledger,
)
from reasoning.llm_harness import invoke_llm_agent

SHAPING_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "prompts",
    "epic-shaping-system-prompt.md",
)


def load_shaping_prompt() -> str:
    with open(SHAPING_PROMPT_PATH) as f:
        return f.read()


def build_shaping_message(epic: Epic) -> str:
    """The user turn for Phase A. The raw Rally Epic is UNTRUSTED external content, so it is wrapped in
    <user_input>...</user_input> delimiters (§6.2 prompt-injection mitigation); the shaping system prompt
    instructs the model to treat delimited content as data only."""
    from runtime import wrap_user_input

    lines = [
        f"## Rally Epic {epic.formatted_id} — {epic.name}".rstrip(),
        "",
        "### Description",
        epic.description.strip(),
        "",
    ]
    if epic.acceptance_criteria:
        lines += [
            "### Acceptance Criteria",
            *[f"- {a}" for a in epic.acceptance_criteria],
            "",
        ]
    if epic.nfrs:
        lines += ["### Non-Functional Requirements", *[f"- {n}" for n in epic.nfrs], ""]
    if epic.dependencies:
        lines += ["### Dependencies", *[f"- {d}" for d in epic.dependencies], ""]
    if epic.linked_items:
        lines += [
            "### Linked Features / Stories",
            *[f"- {i}" for i in epic.linked_items],
            "",
        ]
    epic_block = wrap_user_input("\n".join(lines))
    return (
        epic_block
        + "\n\nLift signals into the section buckets per your rules. Output JSON only."
    )


def _norm(s: str) -> str:
    """Whitespace-collapsed, lowercased — for the verbatim-span containment check (tolerant of wrapping)."""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


_NUM = re.compile(r"\d+(?:\.\d+)?")


def _value_grounded(value: str, span: str) -> bool:
    """C-1 guard: the rendered `value` must be GROUNDED in its (already verbatim-verified) `span`.

    Two rules, chosen to block fabrication while still permitting the light wording-normalization the
    shaping prompt allows (e.g. "P95 < 5 minutes" from "...within 5 minutes at the 95th percentile"):

      1. HARD — every numeric token in `value` must appear in `span`. This prevents fabricating or
         ALTERING any quantitative requirement (the C-1 failure: attaching "1 millisecond" to a span
         that says "5 minutes"). Legit normalizations keep the same numbers, so they pass.
      2. SOFT — `value` must share at least one salient (4+ char) lexical token with `span` (prefix or
         substring match, tolerant of morphology like available/availability). Blocks attaching a wholly
         unrelated/injected value to a real span; allows synonyms/abbreviations.
    """
    nv, ns = _norm(value), _norm(span)
    if not set(_NUM.findall(nv)).issubset(set(_NUM.findall(ns))):
        return False
    vt = re.findall(r"[a-z]{4,}", nv)
    if not vt:
        return True  # nothing lexical to ground; the span is already verbatim-present
    span_tokens = re.findall(r"[a-z]{3,}", ns)
    for w in vt:
        if any(w[:4] == t[:4] or w in t or t in w for t in span_tokens):
            return True
    return False


def validate_ledger(
    model_json: dict[str, Any], epic: Epic, provenance: EpicProvenance
) -> EpicSignalLedger:
    """Deterministic repair/validation of the agent's raw output → a conforming EpicSignalLedger.

    Enforces the extractive, span-grounded guarantee: known section keys only; each signal has a
    non-empty `epic_span` that verbatim-occurs in the Epic (else dropped) AND a `value` grounded in that
    span (no fabricated/altered numbers, shared lexical content — see `_value_grounded`); shape normalized.
    """
    ledger = empty_ledger(provenance)
    sections_out: dict[int, LedgerSection] = {s.num: s for s in ledger.sections}
    raw_sections = (model_json or {}).get("sections", {}) or {}
    epic_corpus = _norm(epic.raw_text())

    for raw_key, raw_signals in raw_sections.items():
        try:
            num = int(str(raw_key).strip().lstrip("§"))
        except (TypeError, ValueError):
            continue
        if num not in VALID_SECTION_NUMS or not isinstance(raw_signals, list):
            continue
        target = sections_out[num]
        for sig in raw_signals:
            if not isinstance(sig, dict):
                continue
            value = str(sig.get("value", "")).strip()
            span = str(sig.get("epic_span", "")).strip()
            kind = str(sig.get("kind", "")).strip() or "signal"
            if not value or not span:
                continue
            # EXTRACTIVE GUARANTEE (1/2): the span must verbatim-occur in the Epic.
            if _norm(span) not in epic_corpus:
                continue
            # EXTRACTIVE GUARANTEE (2/2): the value must be grounded in that span (no invented numbers,
            # shared lexical content). Blocks a fabricated requirement riding on a real span (C-1).
            if not _value_grounded(value, span):
                continue
            target.signals.append(LedgerSignal(value=value, kind=kind, epic_span=span))
    return ledger


def shape_epic(epic: Epic, model_fn: Any = None) -> EpicSignalLedger:
    """Run Phase A: invoke the one LlmAgent (extractive) and validate into an Epic Signal Ledger.

    `model_fn` injects a model in tests; in production it is None and the live Gemini provider is used
    (same path as recommend_architecture). If the live path is unconfigured, invoke_llm_agent raises
    NotImplementedError, which the orchestrator/server surfaces as task failure.
    """
    provenance = EpicProvenance(
        source="rally",
        formatted_id=epic.formatted_id,
        object_version=epic.object_version,
        last_update_date=epic.last_update_date,
    )
    system_prompt = load_shaping_prompt()
    user_message = build_shaping_message(epic)
    model_output = invoke_llm_agent(system_prompt, user_message, model_fn=model_fn)
    if isinstance(model_output, str):
        try:
            model_output = json.loads(model_output)
        except json.JSONDecodeError:
            model_output = {}
    return validate_ledger(model_output, epic, provenance)
