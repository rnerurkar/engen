"""Tool 3 — adr_compliance_check: deterministic ADR policy enforcement.

For each (integration, target_tech, pattern), query the ADR Constraint Store by key
(source_tech, target_tech, functional_category, r_factor), evaluate each matching rule's
predicate via the no-eval interpreter, and emit pass / flag / reject. attested_adrs[] is the
audit trail that flows into the design contract.

The rule CONTENT is human-authored (EA office). This is the deterministic evaluation engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .adr_predicate import check_identifier_ceiling, evaluate


@dataclass
class AdrRule:
    adr_id: str
    key: dict[str, Any]  # {source_tech, target_tech, functional_category, r_factor}
    predicate: str
    action: str  # PASS | FLAG | REJECT
    tests: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceResult:
    integration_id: str
    result: str  # pass | flag | reject
    attested_adrs: list[Any] = field(default_factory=list)
    violations: list[Any] = field(default_factory=list)
    flags: list[Any] = field(default_factory=list)


def _rule_applies(rule: AdrRule, key: dict[str, Any]) -> bool:
    """A rule applies if every specified key dimension matches (empty/'*' = wildcard)."""
    for dim, val in rule.key.items():
        if val in ("", "*"):
            continue
        if key.get(dim, "").lower() != val.lower():
            return False
    return True


def validate_rule_tests(rule: AdrRule) -> None:
    """CI guard: a rule must ship >=3 positive and >=3 negative tests, and its predicate must
    respect the identifier ceiling. Each test's predicate result must match its expectation."""
    check_identifier_ceiling(rule.predicate)
    pos = rule.tests.get("positive", [])
    neg = rule.tests.get("negative", [])
    if len(pos) < 3 or len(neg) < 3:
        raise ValueError(
            f"{rule.adr_id}: needs >=3 positive and >=3 negative tests "
            f"(have {len(pos)}/{len(neg)})"
        )
    for t in pos:
        if not evaluate(rule.predicate, t):
            raise ValueError(
                f"{rule.adr_id}: positive test did not trip predicate: {t}"
            )
    for t in neg:
        if evaluate(rule.predicate, t):
            raise ValueError(f"{rule.adr_id}: negative test tripped predicate: {t}")


def adr_compliance_check(
    integration_id: str,
    key: dict[str, Any],
    eval_context: dict[str, Any],
    rules: list[AdrRule],
) -> ComplianceResult:
    """Evaluate all applicable ADR rules for one integration. REJECT dominates FLAG dominates PASS."""
    res = ComplianceResult(integration_id=integration_id, result="pass")
    worst = "pass"
    for rule in rules:
        if not _rule_applies(rule, key):
            continue
        tripped = evaluate(rule.predicate, eval_context)
        if not tripped:
            res.attested_adrs.append(
                {
                    "integration_id": integration_id,
                    "adr_id": rule.adr_id,
                    "result": "pass",
                }
            )
            continue
        if rule.action == "REJECT":
            res.violations.append(rule.adr_id)
            res.attested_adrs.append(
                {
                    "integration_id": integration_id,
                    "adr_id": rule.adr_id,
                    "result": "reject",
                }
            )
            worst = "reject"
        elif rule.action == "FLAG":
            res.flags.append(rule.adr_id)
            res.attested_adrs.append(
                {
                    "integration_id": integration_id,
                    "adr_id": rule.adr_id,
                    "result": "flag",
                }
            )
            if worst != "reject":
                worst = "flag"
        else:  # PASS action whose predicate tripped = an explicit attestation
            res.attested_adrs.append(
                {
                    "integration_id": integration_id,
                    "adr_id": rule.adr_id,
                    "result": "pass",
                }
            )
    res.result = worst
    return res
