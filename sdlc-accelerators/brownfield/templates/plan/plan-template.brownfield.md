# Brownfield Migration Plan — <Application Name>

> Generated via `/speckit.plan.draft`, then reviewed via `/speckit.plan.review` (Plan Gate).
> One decision block per integration. R-factor vocabulary is FIXED:
> rehost | replatform | refactor | rearchitect | retire.

## Migration Strategy (Application-Wide)
- **Overall approach:** <strangler-fig | phased | big-bang — and why>
- **Cutover sequencing principle:** <low-risk first, critical last>

## Per-Integration Decisions

### Integration: INT-XXX — <short name>
- **R-factor:** <rehost | replatform | refactor | rearchitect | retire>
- **Cutover strategy:** <big-bang | strangler-fig | blue-green | dual-publish | scheduled-job>
- **Coexistence window:** <e.g. "48h dual-publish" | "14-day soak" | "N/A">
- **Phase:** <1 (read-path) | 2 (write-path) | 3 (decommission)>
- **Rollback path:** <how to revert this integration, and the rollback SLA>
- **Coupling:** <integrations that must cut over together, if any>
- **Context dimensions:** <criticality, data_size_class, compliance_regime, messaging_pattern,
  region_constraints, partner_constraints — used by map_current_to_target>

## Review Notes (populated by `/speckit.plan.review`)
<EA architect / LOB lead comments and resolutions. Plan enters `reviewed` state once resolved.>
