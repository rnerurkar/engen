# Brownfield Migration Spec — <Application Name>

> Generated via `/speckit.specify` (brownfield preset). The csa-extractor pre-fills integration
> blocks from the CSA diagram; you supply the fields the diagram can't reveal. Every integration
> must satisfy the 8 migration-readiness signals or `validate_spec` will BLOCK.

## Application Summary
<What the application does today, its runtime, and the business driver for migration.>

## Modernization Scope
<Which integrations are IN scope for conversion (whole or selective). Out-of-scope integrations
remain as-is and appear as coexistence boundaries in the transition diagrams.>

## Integration Inventory

### Integration: INT-XXX — <short name>
- **Technology + version:** <e.g. "IBM MQ 9.1" — specific tech+version, NOT "legacy messaging">   [Signal: CSA Completeness]
- **Integration type:** <sync API | async messaging | batch | DB link | file transfer>           [Signal: Integration Type]
- **Data flow direction:** <read-only | write-only | bidirectional>                               [Signal: Data Flow Direction]
- **Criticality:** <critical | high | medium | low>                                               [Signal: Criticality Rating]
- **Coexistence constraint:** <dual-read | dual-write | hard-cutover | N/A>                        [Signal: Coexistence Constraints]
- **API surface / contract:** <OpenAPI/WSDL/endpoint URL, or "internal — none">                   [Signal: API Surface]
- **State management:** <session (sticky) | transaction (2PC/XA) | cache (shared) | stateless>    [Signal: State Management]
- **Data volume + SLA:** <volume per period; latency SLA; throughput>                              [Signal: Data Volume + SLA]
- **Target intent:** <what this should become in the TSA, if known>
- **Hard rejections:** <technologies/approaches explicitly disallowed for this integration>

## Non-Functional Requirements (Application-Wide)
- Availability / DR target:
- Compliance regime:
- Region constraints:
