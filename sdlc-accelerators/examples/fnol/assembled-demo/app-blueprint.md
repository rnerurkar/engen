# Application Blueprint — FNOL intake

> Solution: `fnol` · Archetype: agentic · Overall confidence: **high**

## §1. Application Overview

FNOL intake. Primary pattern: **SequentialAgent**. This solution composes 1 pattern(s) into an agentic workflow of 3 agents.

## §2. Component Topology Diagram

![Component Topology](diagrams/component-topology.png)

**Agent topology:**

- **fnol_coordinator** (SequentialAgent): Orchestrates
  - **extract_details** (LlmAgent): Extract — tools: claims-db-mcp, coverage_calculator_fn
  - **severity_classifier** (LlmAgent): Classify — tools: severity_classifier_fn, body-shop-a2a

## §3. Architecture Patterns

| Pattern | Role | Nesting | Confidence |
|---|---|---|---|
| SequentialAgent | orchestration | — | high |

## §4. Application Tech Stack

| Layer | Choice |
|---|---|
| Agent framework | Google ADK |
| Models | gemini-2.0-flash |
| Skills (with provenance) | adk-agents@2.1.0 |

## §5. DevSecOps Stack

Model Armor: strict. CI: Cloud Build. CD: Harness (downstream). Signing: cosign + Binary Authorization.

## §6. HA/DR Guidance

Strategy: **Warm Standby**. Primary: us-east1 · DR: us-central1.

## §7. HA/DR Lifecycle Diagrams

![HA/DR Lifecycle](diagrams/hadr-lifecycle.png)

## §8. Architecture Decision Log

| # | Decision | Rationale |
|---|---|---|
| 1 | Primary pattern = SequentialAgent | Derived from spec ordering words |
| 5 | Use A2A agent body-shop-a2a | Partner operates own system (A2A > MCP > Build) |

## §9. Non-Functional Requirements

| NFR | Target |
|---|---|
| availability | 99.9% |

