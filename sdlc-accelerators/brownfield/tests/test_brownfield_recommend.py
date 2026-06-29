"""Brownfield Tool 2 recommend_architecture: injected fn, live provider, and graceful degrade."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from brownfield import recommend_architecture as ra

SUB = {
    "integration_id": "INT-004",
    "r_factor": "refactor",
    "target_tokens": ["aws-sqs"],
    "transition_pattern_ref": "PAT-T-007-dual-publish-mq-sqs",
}


def test_injected_recommend_fn_takes_precedence():
    out = ra.recommend_for_integration(
        SUB, recommend_fn=lambda s: {"pattern_ref": "X", "confidence": 0.9}
    )
    assert out["pattern_ref"] == "X"


def test_degrades_to_review_when_provider_unavailable(monkeypatch):
    provider = ra._load_provider()
    monkeypatch.setattr(provider, "available", lambda: (False, "no creds"))
    out = ra.recommend_for_integration(SUB)
    assert out["requires_review"] is True
    assert out["confidence"] == 0.0
    assert (
        out["pattern_ref"] == "PAT-T-007-dual-publish-mq-sqs"
    )  # falls back to the substitution ref


def test_live_provider_selects_with_confidence(monkeypatch):
    provider = ra._load_provider()
    monkeypatch.setattr(provider, "available", lambda: (True, ""))
    monkeypatch.setattr(
        provider,
        "invoke",
        lambda sp, um: {
            "pattern_ref": "PAT-T-007",
            "confidence": 0.82,
            "rationale": "best fit",
        },
    )
    out = ra.recommend_for_integration(SUB)
    assert out["pattern_ref"] == "PAT-T-007"
    assert out["confidence"] == 0.82
    assert out["requires_review"] is False  # 0.82 >= 0.65


def test_low_confidence_flags_review(monkeypatch):
    provider = ra._load_provider()
    monkeypatch.setattr(provider, "available", lambda: (True, ""))
    monkeypatch.setattr(
        provider, "invoke", lambda sp, um: {"pattern_ref": "P", "confidence": 0.4}
    )
    out = ra.recommend_for_integration(SUB)
    assert out["requires_review"] is True  # 0.4 < 0.65


def test_prompt_is_bound_verbatim(monkeypatch):
    """The human-authored reasoning prompt is passed to the provider unmodified."""
    provider = ra._load_provider()
    captured = {}
    monkeypatch.setattr(provider, "available", lambda: (True, ""))
    monkeypatch.setattr(
        provider,
        "invoke",
        lambda sp, um: (
            captured.update(prompt=sp) or {"pattern_ref": "P", "confidence": 0.9}
        ),
    )
    ra.recommend_for_integration(SUB)
    assert captured["prompt"] == ra.BROWNFIELD_RECOMMEND_PROMPT


def test_pipeline_uses_live_reasoning_by_default(monkeypatch):
    """Without an injected recommend_fn, the pipeline routes through the live reasoning module."""
    import json

    from brownfield.map_current_to_target import SubstitutionRow
    from brownfield.pipeline import run_brownfield_pipeline

    ref = ROOT / "examples/vsphere-mpa-aws-spa/inputs"
    rows = [
        SubstitutionRow(**r)
        for r in json.loads((ref / "substitution-table.json").read_text())["rows"]
    ]

    provider = ra._load_provider()
    monkeypatch.setattr(provider, "available", lambda: (True, ""))
    monkeypatch.setattr(
        provider,
        "invoke",
        lambda sp, um: {"pattern_ref": "LLM-PICK", "confidence": 0.9},
    )

    result = run_brownfield_pipeline(
        (ref / "spec.md").read_text(), (ref / "plan.md").read_text(), rows, adr_rules=[]
    )  # NO recommend_fn -> live reasoning path
    sels = result["design_contract"]["pattern_selections"]
    assert all(s["pattern_ref"] == "LLM-PICK" for s in sels)
    assert all(s["requires_review"] is False for s in sels)
