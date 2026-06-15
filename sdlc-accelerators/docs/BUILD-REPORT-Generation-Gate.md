# Build Report — Server-Side Generation Governance Gate (Path A)

`/accelerator.generate` now verifies server-side that no Critical or High findings remain
before code generation. **69 tests passing (5 new + 1 e2e), clean lint.**

## Flow
1. `assess_result` writes the findings Markdown to a **GCS bucket** and records a pointer in
   **AlloyDB** (task_id, owner_id, gcs_uri, has_blocking).
2. `/accelerator.generate` → coding agent calls **`verify_generation_gate(taskId)`**.
3. The Governance Guardian reads `findings.md` back via the AlloyDB pointer (owner_id-isolated)
   and parses the Critical/High/Medium/Low categories:
   - **Critical or High remain** → `{signal: stop, message}`: resolve the findings, run
     `/accelerator.refresh` to re-validate `.md`↔`.drawio` sync, then re-run `/accelerator.assess`.
   - **Only Medium/Low remain** → writes **one tech-debt JSON per finding** to the GCS
     tech-debt bucket (`status: accepted`, `TD-<year>-<task>-NNN`, severity, section, owner),
     returns `{signal: resume, tech_debt_uris}`.

## Components (services/governance-guardian/src/findings_store/)
- `store.py` — FindingsStore: findings.md → GCS object + AlloyDB pointer row; read-back by pointer.
  GCS put/get are injectable seams; pointer model + key scheme + reference backing are real.
- `generation_gate.py` — parse_findings_md (severity buckets) + verify_generation_gate
  (block on critical/high; else write tech-debt JSON per medium/low).

## Server wiring (server/app.py)
- `assess_result` now persists findings to the store (GCS + AlloyDB pointer).
- New tool **`verify_generation_gate`** (5th GG tool), auth-gated, owner_id-isolated.

## Validations (tested)
- ✅ findings.md parsed into critical/high/medium/low buckets
- ✅ Gate STOPS on critical or high, with the resolve+refresh+reassess message
- ✅ Gate RESUMES on only medium/low AND writes one tech-debt JSON per finding to GCS
- ✅ FindingsStore: correct gs:// URI, AlloyDB pointer, read-back, GCS put seam invoked
- ✅ End-to-end via the GG server through auth: assess(critical+high) → persist → gate blocks;
   resolved → gate resumes + tech-debt JSON written to GCS

## Policy note (beyond the original doc, per instruction)
The original doc gated on **showstopper = critical only** via `recordTechDebt`. Path A broadens
this to **Critical OR High blocks**, persists findings to GCS with an AlloyDB pointer, moves the
verdict server-side (`verify_generation_gate`), and writes per-finding tech-debt JSON for
Medium/Low. The architecture, developer guide, and runbook were updated to describe this.

## Seams (live wiring)
- GCS put/get (google.cloud.storage) for findings.md + tech-debt JSON
- AlloyDB-backed pointer table with RLS (in-memory reference today)
