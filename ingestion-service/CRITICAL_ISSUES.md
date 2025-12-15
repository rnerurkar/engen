# Ingestion Service - Critical Issues Analysis

# Ingestion Service — Updated Critical Issues (Dec 15, 2025)

Last Updated: Dec 15, 2025 — This document reflects current, validated priorities. Historical critique and outdated content have been removed to avoid confusion.

This document reflects the current state of `ingestion-service` after recent refactors (two-phase commit, rollback, parallel preparation, staging/checkpoints, SharePoint pagination/backoff). It replaces prior items with an up-to-date, prioritized list and concrete remediation actions.

## Objectives Compliance
- Synchronized traversal: Met — single pass per pattern with staged prepare.
- Simultaneous stream preparation: Met — `asyncio.gather` in prepare phase.
- Atomic commit with rollback: Met — sequential commit with reverse-order rollback.
- Content atomization: Met — robust parsing and chunked writes with retries.
- Idempotency and resume: Met — checkpoints and skip of completed patterns.

## Critical (must fix ASAP)
- Configurable pages library usage
    - Problem: `clients/sharepoint.py::fetch_page_html` hardcodes `SitePages` instead of using `Config.SP_PAGES_LIBRARY`.
    - Impact: Breaks on tenants with non-standard pages library naming.
    - Action: Replace constant with `self.cfg.SP_PAGES_LIBRARY`; add validation in `Config`.

- Pre-flight environment/resource checks
    - Problem: No upfront verification of GCP credentials, Discovery Engine data store/branch, Vector Index endpoint/deployed index, Firestore availability, GCS bucket ACL/write.
    - Impact: Failures surface mid-ingestion; wasted cycles and partial work before rollback.
    - Action: Add `verify_environment()` in `main.py` to probe each dependency with short timeouts; abort early with clear logs.

## High Priority
- Cross-pattern concurrency controls
    - Problem: Patterns processed sequentially; pipeline could be faster with bounded concurrency.
    - Impact: Lower throughput on large catalogs.
    - Action: Add semaphore-based concurrency (e.g., `asyncio.Semaphore(N)`) to run up to N transactions in parallel while preserving per-transaction atomicity.

- SharePoint client robustness and observability
    - Problem: Client is sync; lacks structured metrics; retry/backoff exists but could include jitter and circuit-breaker.
    - Impact: Throughput constraints under SharePoint rate limits; harder ops visibility.
    - Action: Introduce jitter on retries; optional async variant using `aiohttp`; add counters/timers for catalog/page fetches.

## Medium Priority
- Structured metrics and tracing
    - Problem: Logging is informative but lacks metrics/traces.
    - Impact: Harder SLOs and incident diagnostics.
    - Action: Add lightweight metrics (e.g., Prometheus client) and optional OpenTelemetry spans around prepare/commit/rollback.

- Fine-grained idempotency markers
    - Problem: Checkpoints track committed transactions but not partial per-stream completion.
    - Impact: On partial external failures, recovery always re-runs full prepare.
    - Action: Extend checkpoint schema to include per-stream prepared/committed flags for smarter resumes.

- Config validations and sane defaults
    - Problem: `Config` validates presence but not format (e.g., IDs, URIs) nor consistency.
    - Impact: Misconfiguration reaches runtime.
    - Action: Add format checks (regex/prefix), ensure `PROJECT_ID`, endpoints, and IDs align; warn on risky defaults.

## Low Priority
- Async SharePoint HTTP
    - Problem: `requests` is blocking; acceptable today.
    - Impact: Minor latency; fewer connections.
    - Action: Optional migration to `aiohttp` with shared session and backoff.

- Minor parser enhancements
    - Problem: Content parser covers common headings and elements; edge cases may remain.
    - Impact: Rare content misses.
    - Action: Add rules for additional HTML patterns (callouts, custom web parts) as encountered.

## Verification Tests
- Environment pre-flight: All probes succeed/fail fast with clear messages.
- Transaction atomicity: Inject failures in A/B/C and confirm rollback and no side-effects.
- Vector upsert timeout/retry: Simulate timeouts and verify retries and eventual success/failure handling.
- Firestore chunking: Documents >500 validate chunk logic; retries succeed under transient errors.
- SharePoint pagination: Large catalogs iterate via `@odata.nextLink` correctly.

## Implementation Pointers
- `clients/sharepoint.py`: Use `self.cfg.SP_PAGES_LIBRARY` in page queries; add jitter and optional circuit-breaker.
- `main.py`: Add `verify_environment()` pre-flight; add semaphore for bounded concurrency across patterns.
- `transaction_manager.py`: Extend `TransactionState.to_dict()` for per-stream flags if implementing fine-grained idempotency.
- `processors/*`: Emit metrics counters/timers; retain current validation and retry patterns.

## Next Steps
Implement pages library configurability and pre-flight checks first (Critical).
Add bounded concurrency for pattern-level throughput (High).
Layer metrics/tracing and enhanced checkpoints (Medium).
Consider async SharePoint I/O migration (Low) if throughput is a bottleneck.
