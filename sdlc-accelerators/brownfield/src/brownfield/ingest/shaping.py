"""Phase A — brownfield agentic shaping (extractive, span-grounded).

The Solution Accelerator Agent's `create_epic_signal_ledger` FunctionTool runs ONE bounded, extractive
LLM pass over a Rally Epic and emits a raw JSON shape; this module's `validate_ledger` deterministically
repairs it into a conforming Brownfield Epic Signal Ledger. Guarantees (identical to greenfield):

  1. every signal's `epic_span` must VERBATIM occur in the Epic (else dropped), and
  2. its `value` must be GROUNDED in that span — no fabricated/altered numbers, shared lexical content
     (`_value_grounded`) — so the agent cannot fabricate or alter requirements.

The model output shape:
  { "summary": {value, epic_span}, "modernization_scope": {value, epic_span},
    "integrations": [ {int_id, name, fields: {technology|type|direction|criticality|coexistence|
                       api_surface|state|volume_sla: {value, epic_span}}, target_intent?: {value,epic_span}} ],
    "nfrs": [ {value, kind, epic_span} ] }
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from brownfield.ingest.epic_models import (
    SIGNAL_KEYS,
    BrownfieldEpicSignalLedger,
    Epic,
    EpicProvenance,
    IntegrationSignal,
    empty_ledger,
)

_PROMPT = os.path.join(
    os.path.dirname(__file__), "prompts", "epic-shaping-system-prompt.brownfield.md"
)
_NUM = re.compile(r"\d+(?:\.\d+)?")


def load_shaping_prompt() -> str:
    with open(_PROMPT, encoding="utf-8") as f:
        return f.read()


def build_shaping_message(epic: Epic) -> str:
    from brownfield.runtime import wrap_user_input

    body = (
        "Rally Epic to shape into an integration-keyed Brownfield Epic Signal Ledger.\n\n"
        f"FormattedID: {epic.formatted_id}\nName: {epic.name}\n\n"
        f"Description:\n{epic.description}\n\n"
        + (
            f"Integrations:\n{epic.integrations_text}\n\n"
            if epic.integrations_text
            else ""
        )
        + (
            "Acceptance criteria:\n"
            + "\n".join(f"- {a}" for a in epic.acceptance_criteria)
            + "\n\n"
            if epic.acceptance_criteria
            else ""
        )
        + (
            "NFRs:\n" + "\n".join(f"- {n}" for n in epic.nfrs) + "\n"
            if epic.nfrs
            else ""
        )
    )
    # §6.2 — the Rally Epic is untrusted; wrap it so the model treats it as data, not instructions.
    return wrap_user_input(body)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _value_grounded(value: str, span: str) -> bool:
    """Same guard as greenfield: every number in `value` must appear in `span`, and `value` must share
    at least one salient (4+ char) lexical token with `span` (prefix/substring, morphology-tolerant)."""
    nv, ns = _norm(value), _norm(span)
    if not set(_NUM.findall(nv)).issubset(set(_NUM.findall(ns))):
        return False
    vt = re.findall(r"[a-z]{4,}", nv)
    if not vt:
        return True
    span_tokens = re.findall(r"[a-z]{3,}", ns)
    return any(any(w[:4] == t[:4] or w in t or t in w for t in span_tokens) for w in vt)


def _grounded_field(raw: Any, corpus: str) -> dict[str, Any] | None:
    """Validate one {value, epic_span} field; return the cleaned field or None if it fails the guards."""
    if not isinstance(raw, dict):
        return None
    value = str(raw.get("value", "")).strip()
    span = str(raw.get("epic_span", "")).strip()
    if not value or not span:
        return None
    if _norm(span) not in corpus:
        return None
    if not _value_grounded(value, span):
        return None
    return {"value": value, "epic_span": span}


def validate_ledger(
    model_json: dict[str, Any], epic: Epic, provenance: EpicProvenance
) -> BrownfieldEpicSignalLedger:
    ledger = empty_ledger(provenance)
    mj = model_json or {}
    corpus = _norm(epic.raw_text())

    s = _grounded_field(mj.get("summary"), corpus)
    if s:
        ledger.summary = s
    sc = _grounded_field(mj.get("modernization_scope") or mj.get("scope"), corpus)
    if sc:
        ledger.scope = sc

    seen_ids = set()
    for raw in mj.get("integrations") or []:
        if not isinstance(raw, dict):
            continue
        int_id = str(raw.get("int_id", "")).strip().upper()
        if not re.fullmatch(r"INT-\d+", int_id) or int_id in seen_ids:
            continue
        seen_ids.add(int_id)
        name = str(raw.get("name", "")).strip()
        fields = {}
        for k in SIGNAL_KEYS:
            f = _grounded_field((raw.get("fields") or {}).get(k), corpus)
            if f:
                fields[k] = f
        target = _grounded_field(raw.get("target_intent"), corpus) or {}
        if fields or name:
            ledger.integrations.append(
                IntegrationSignal(
                    int_id=int_id, name=name, fields=fields, target_intent=target
                )
            )

    for raw in mj.get("nfrs") or []:
        f = _grounded_field(raw, corpus)
        if f:
            ledger.nfrs.append(
                {
                    "value": f["value"],
                    "kind": str((raw or {}).get("kind", "nfr")).strip() or "nfr",
                    "epic_span": f["epic_span"],
                }
            )

    # Stable order by INT id.
    ledger.integrations.sort(key=lambda ig: ig.int_id)
    return ledger


def shape_epic(epic: Epic, model_fn: Any = None) -> BrownfieldEpicSignalLedger:
    """Run Phase A: invoke the agent's shaping (extractive) and validate into the ledger.
    `model_fn(system_prompt, user_message) -> dict` is injectable for tests; else the live provider runs."""
    system_prompt = load_shaping_prompt()
    user_message = build_shaping_message(epic)
    if model_fn is not None:
        raw = model_fn(system_prompt, user_message)
    else:
        # §2.1/§2.2/§3.1/§3.2/§5.2 — live shaping via the shared runtime (retry + circuit breaker +
        # secondary-model fallback + pooled async client + generation span). The Gemini provider is the
        # seam; tests inject model_fn instead.
        from brownfield.runtime import invoke_llm

        raw = invoke_llm(
            system_prompt, user_message, agent_id="solution_accelerator_agent"
        )
    if isinstance(raw, str):
        raw = json.loads(raw)
    return validate_ledger(raw, epic, epic.provenance())
