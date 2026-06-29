"""Tests for /accelerator.epic-to-spec — the CSA-fusion front door.

Deterministic (no LLM): an Epic whose Modernization Scope table names CSA components, fused with an
upstream CSA architecture.md, yields a component-scoped, disposition-bearing, specify-conformant spec.md
that passes the SAME 8-signal readiness gate `/speckit.plan` relies on.

Run: python brownfield/tests/test_brownfield_epic_to_spec.py  (or via pytest).
"""

from __future__ import annotations

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, _SRC)

from brownfield.ingest.orchestrator import run_epic_to_spec  # noqa: E402

# Upstream CSA Agent output (separate system, outside this preset). Component + integration inventory,
# keyed by stable IDs; the integration signals use the validator's accepted enum values.
CSA_ARCHITECTURE_MD = """# Current-State Architecture — Order Management Platform

## Application Summary
A monolithic order-management platform on vSphere serving retail checkout.

## Component Inventory
### Component: CSA-COMP-001 — Order Service
- **Technology:** Java 8 / Spring Boot 1.5
- **Hosting:** on-prem VM (RHEL 7)
- **Data store:** Oracle 12c
- **Dependencies:** CSA-COMP-002, CSA-COMP-003

### Component: CSA-COMP-002 — Payment Gateway Adapter
- **Technology:** Java 8 / IBM API Connect 10
- **Hosting:** on-prem VM (RHEL 7)
- **Data store:** none
- **Dependencies:** CSA-COMP-001

### Component: CSA-COMP-003 — Batch Reconciler
- **Technology:** Perl 5.16 cron jobs
- **Hosting:** on-prem VM (RHEL 6)
- **Data store:** Oracle 12c
- **Dependencies:** CSA-COMP-001

## Integration Inventory
### Integration: INT-001 — Order Service -> Payment Gateway
- **Technology + version:** REST/JSON over HTTPS (TLS 1.2)
- **Integration type:** sync api
- **Data flow direction:** bidirectional
- **Criticality:** critical
- **Coexistence constraint:** dual-write
- **API surface / contract:** OpenAPI 3.0 /payments
- **State management:** stateless
- **Data volume + SLA:** 2000 tps p99 < 250ms
- **Components:** CSA-COMP-001, CSA-COMP-002

### Integration: INT-002 — Order Service -> Inventory Queue
- **Technology + version:** IBM MQ 9.1
- **Integration type:** async messaging
- **Data flow direction:** write-only
- **Criticality:** high
- **Coexistence constraint:** dual-write
- **API surface / contract:** message contract v3
- **State management:** stateless
- **Data volume + SLA:** 500K messages/day
- **Components:** CSA-COMP-001

### Integration: INT-003 — Payment Gateway -> Ledger DB
- **Technology + version:** Oracle 12c DB link
- **Integration type:** db link
- **Data flow direction:** read-only
- **Criticality:** medium
- **Coexistence constraint:** dual-read
- **API surface / contract:** PL/SQL package PKG_LEDGER
- **State management:** stateless
- **Data volume + SLA:** 1M rows/day
- **Components:** CSA-COMP-002
"""

EPIC = {
    "formatted_id": "E7700",
    "name": "Modernize Order Management to AWS",
    "object_version": 12,
    "last_update_date": "2026-06-28",
    "description": (
        "Move the order platform off vSphere into AWS.\n\n"
        "## Modernization Scope\n"
        "| Component | Disposition | AWS Target | Rationale |\n"
        "|-----------|-------------|-----------|-----------|\n"
        "| CSA-COMP-001 | Refactor | ECS Fargate + Aurora PostgreSQL | break the monolith |\n"
        "| CSA-COMP-002 | Rehost | EC2 (lift-and-shift) | vendor-locked adapter |\n"
    ),
    "nfrs": [
        "exit the on-prem datacenter by Q4",
        "no checkout downtime during cutover",
    ],
    "acceptance_criteria": ["all payment flows pass parity tests"],
}


def test_fusion_pipeline_and_gate():
    out = run_epic_to_spec(EPIC, csa_architecture_md=CSA_ARCHITECTURE_MD)
    assert out["mode"] == "fusion"
    spec = out["spec_md"]

    # Component-scoped sections carry the disposition.
    assert "### Component: CSA-COMP-001 — Order Service (Disposition: Refactor)" in spec
    assert "(Disposition: Rehost)" in spec
    # Disposition-specific migration guidance is present.
    assert "strangler-fig" in spec and "lift-and-shift" in spec.lower()

    # Cross-walk buckets.
    rs = out["resolved_scope"]
    assert {u["component_id"] for u in rs["in_scope"]} == {
        "CSA-COMP-001",
        "CSA-COMP-002",
    }
    assert rs["out_of_scope"] == ["CSA-COMP-003"]
    assert rs["unresolved"] == []
    assert rs["invalid_disposition"] == []

    # CSA-sourced integration inventory flows in and passes the SAME readiness gate /plan uses.
    assert "### Integration: INT-001 — Order Service -> Payment Gateway" in spec
    gate = out["blueprint_gate"]
    assert gate["blocked"] is False and gate["migration_readiness_score"] == 100

    # Provenance covers BOTH sources (Epic + CSA hash).
    prov = out["provenance"]
    assert prov["formatted_id"] == "E7700" and prov["object_version"] == 12
    assert prov["csa_hash"] and len(prov["csa_hash"]) == 12

    # Scope ledger sidecar.
    led = out["modernization_scope_ledger"]
    assert led["schema"] == "brownfield-modernization-scope-ledger/v1"
    assert led["provenance"]["csa_hash"] == prov["csa_hash"]
    assert out["empty"] is False


def test_unresolved_component_blocks():
    """An Epic that scopes a component the CSA does not contain is surfaced and blocks."""
    epic = {
        "formatted_id": "E7701",
        "name": "Bad scope",
        "object_version": 1,
        "description": (
            "## Modernization Scope\n"
            "| Component | Disposition | AWS Target |\n"
            "|---|---|---|\n"
            "| CSA-COMP-999 | Refactor | ECS |\n"
        ),
    }
    out = run_epic_to_spec(epic, csa_architecture_md=CSA_ARCHITECTURE_MD)
    assert out["resolved_scope"]["unresolved"] == ["CSA-COMP-999"]
    assert out["scope_blocked"] is True and out["empty"] is True
    assert "CSA-COMP-999" in out["spec_md"]


def test_invalid_disposition_flagged():
    """A recognized component with an unsupported disposition is flagged (not Refactor/Rehost)."""
    epic = {
        "formatted_id": "E7702",
        "name": "Replatform attempt",
        "object_version": 1,
        "description": (
            "## Modernization Scope\n"
            "| Component | Disposition | AWS Target |\n"
            "|---|---|---|\n"
            "| CSA-COMP-001 | Replatform | EKS |\n"
            "| CSA-COMP-002 | Rehost | EC2 |\n"
        ),
    }
    out = run_epic_to_spec(epic, csa_architecture_md=CSA_ARCHITECTURE_MD)
    assert out["resolved_scope"]["invalid_disposition"] == ["CSA-COMP-001"]


def test_legacy_path_without_csa():
    """No CSA architecture.md -> legacy extractive path still produces a spec (back-compat)."""

    def _model_fn(_sys, _user):
        def f(v):
            return {"value": v, "epic_span": v}

        return {
            "summary": f("Order platform"),
            "integrations": [
                {
                    "int_id": "INT-001",
                    "name": "Pay",
                    "fields": {
                        "technology": f("Java 8"),
                        "type": f("sync API"),
                        "direction": f("bidirectional"),
                        "criticality": f("high"),
                        "coexistence": f("dual-write"),
                        "api_surface": f("OpenAPI 3.0"),
                        "state": f("stateless"),
                        "volume_sla": f("2000 tps"),
                    },
                }
            ],
            "nfrs": [],
        }

    out = run_epic_to_spec(
        {
            "formatted_id": "E1",
            "description": "Java 8 sync API bidirectional high dual-write "
            "OpenAPI 3.0 stateless 2000 tps",
        },
        model_fn=_model_fn,
    )
    assert out["mode"] == "legacy-extractive"
    assert "Integration Inventory" in out["spec_md"]


if __name__ == "__main__":
    test_fusion_pipeline_and_gate()
    test_unresolved_component_blocks()
    test_invalid_disposition_flagged()
    test_legacy_path_without_csa()
    print("OK — epic-to-spec fusion checks passed")
