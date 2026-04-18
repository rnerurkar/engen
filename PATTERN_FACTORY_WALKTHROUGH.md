# The Pattern Factory Workflow — A Plain English Walkthrough

Think of Pattern Factory as an assembly line with **7 phases**. A user uploads an architecture diagram, and the system generates documentation (including HA/DR sections with visual diagrams) and deployable code for it — with human checkpoints along the way.

The front-end is a **React 18 + Vite single-page application (SPA)** presenting a 5-step chevron-style wizard (Input → Doc Review → Code Gen → Code Review → Publish). It communicates with the Orchestrator via a single `POST /invoke` BFF endpoint. Workflow state is persisted to **AlloyDB** so users can close the browser and resume later.

### How the Orchestrator works

The Orchestrator is the central "traffic controller." For documentation generation (Phase 1), it uses **ADK Workflow Agents** — lightweight Python classes that run **in the same process** and share a `WorkflowContext` dictionary. The Orchestrator builds a workflow graph at startup:

- A **SequentialAgent** that runs a series of steps one after another.
- A **LoopAgent** nested inside it that iterates generate → HA/DR → review until the document is approved (up to 3 times).

All core logic modules (PatternGenerator, VertexRetriever, PatternReviewer, ServiceHADRRetriever, HADRDocumentationGenerator, HADRDiagramGenerator, HADRDiagramStorage) are instantiated directly and passed into the workflow via the shared context — no network calls, no serialization overhead.

For code generation (Phase 2), the Orchestrator communicates with the artifact agents over **A2A (Agent-to-Agent) HTTP calls**.

Here's the workflow graph at a glance:

```
Phase1DocGenerationWorkflow (SequentialAgent)
  │
  ├── VisionAnalysisStep          ← Gemini Vision: image → description
  │
  ├── DonorRetrievalStep          ← Vertex AI Search: description → donor_context
  │
  ├── ContentRefinementLoop (LoopAgent, max 3 iterations, exit when "approved")
  │     │
  │     ├── PatternGenerateStep   ← Gemini Pro: generate core sections
  │     │
  │     ├── HADRSectionsStep      ← Parallel retrieval + generation → merge into doc
  │     │     • asyncio.gather(retrieve_hadr, extract_donor_hadr)
  │     │     • Generate 4 DR strategies in parallel
  │     │     • Skip on re-iteration if reviewer didn't flag HA/DR
  │     │
  │     └── FullDocReviewStep     ← Review FULL doc (core + HA/DR) → approved / critique
  │
  └── HADRDiagramStep             ← Build 12 diagrams programmatically (< 1s) → upload to GCS
```

---

## Phase 0 — "Resume where you left off" (automatic)

Before anything else, the SPA checks whether the user has an in-progress workflow.

0a. When the React app loads, a `useEffect` hook reads `localStorage` for a saved `engen_workflow_id`.
0b. If found, the app calls the Orchestrator's `resume_workflow` task with that ID. The Orchestrator loads the full workflow snapshot from the **AlloyDB `workflow_state` table** — including the current phase, saved documentation, and any generated code.
0c. The app restores `step`, `docData`, and `codeData` from the server response and jumps the user straight to the step where they left off. A loading spinner is shown while resuming.
0d. If the workflow is no longer active (completed or deleted), the localStorage key is cleared and the user starts fresh.

---

## Phase 1 — "Analyze the diagram and find a donor pattern"

1. The user opens the **Pattern Factory SPA**, uploads an architecture diagram image (e.g., a PNG of a cloud architecture), and types in a title. The UI shows a chevron-style stepper at the top to indicate progress.
2. The app sends this to the **Orchestrator**. The Orchestrator creates a new row in the AlloyDB `workflow_state` table and returns a `workflow_id` that the SPA stores in `localStorage` for future resume. It then builds a `WorkflowContext` seeded with the uploaded image, the title, and references to every core logic module.
3. The first step in the workflow is **VisionAnalysisStep**. It calls `PatternGenerator.generate_search_description()` in-process (via `asyncio.to_thread` so the event loop isn't blocked). Gemini Vision AI looks at the picture and writes a plain-text technical description (e.g., "A Cloud Run service connected to a Cloud SQL database behind a load balancer"). The description is stored in the context.
4. Next, **DonorRetrievalStep** takes that description and the title and calls `VertexRetriever.get_best_donor_pattern()` in-process. This searches the knowledge base (Vertex AI Search) for the closest matching existing design pattern — the **"Donor Pattern."** Think of it like finding a similar recipe before writing a new one. The donor context is stored in the shared `WorkflowContext`.

---

## Phase 2 — "Write the docs, add HA/DR, and review the whole thing — in a loop"

The next part of the workflow is a **LoopAgent** called `ContentRefinementLoop`. It runs up to 3 iterations, each with three steps in sequence. The loop exits early if the reviewer approves the document.

**Step A — Generate the core documentation:**

5. **PatternGenerateStep** calls `PatternGenerator.generate_pattern()` in-process with the image, donor context, title, and any critique from a previous iteration. Gemini Pro writes documentation sections (Problem Statement, Solution, Architecture, etc.).

**Step B — Generate the HA/DR sections:**

6. **HADRSectionsStep** runs next — still inside the loop. On the first iteration it does full HA/DR generation:
   - It scans the generated sections to extract cloud service names (e.g., "Amazon RDS", "AWS Lambda") by matching against a dictionary of 40+ known aliases and common service names. The extracted names are **cached in the context** so they don't need to be re-extracted later.
   - It kicks off **two tasks in parallel** using `asyncio.gather`:
     - **Task 1**: The `ServiceHADRRetriever` searches the dedicated HA/DR knowledge base (Vertex AI Search) for reference documentation about how each service behaves during disasters. All combinations of *service × DR strategy* run in parallel internally.
     - **Task 2**: The `HADRDocumentationGenerator` extracts the donor pattern's existing HA/DR sections as a stylistic template.
   - Once both tasks complete, it builds a pattern context and generates four separate HA/DR sections — one per DR strategy (Backup and Restore, Pilot Light On Demand, Pilot Light Cold Standby, Warm Standby). All four are generated **in parallel internally** (each with a 2-minute timeout). Each section includes sub-sections for Initial Provisioning, Failover, and Failback, with summary tables showing each service's state (Active, Standby, Scaled-Down, or Not-Deployed).
   - The HA/DR sections are merged into the generated documentation under an "HA/DR" key so the reviewer sees the complete document.

7. **On iterations 2 and 3**, the step is smarter: it checks the reviewer's critique. If the critique doesn't mention "HA/DR", "disaster recovery", "high availability", or similar keywords, the step **skips HA/DR regeneration entirely** — it just re-merges the cached HA/DR sections into the freshly generated core sections. This saves significant time and token costs.

**Step C — Review the entire document (core + HA/DR):**

8. **FullDocReviewStep** calls `PatternReviewer.review_pattern()` in-process with the **complete** document — including the HA/DR sections. The reviewer can specifically critique HA/DR quality (e.g., "The Warm Standby failover procedure is too vague"), not just the core sections. It sets an `approved` flag and a `critique` text in the context.
9. If the document is approved, the LoopAgent exits. If not, the critique is available for the next iteration's PatternGenerateStep and HADRSectionsStep to act on.

---

## Phase 2b — "Generate visual HA/DR diagrams"

After the loop finishes, the workflow continues with the final step in the SequentialAgent. This runs with a safety net — if diagrams fail, the text documentation is still delivered.

10. **HADRDiagramStep** generates component diagrams for every combination of DR strategy × lifecycle phase: 4 strategies × 3 phases = **12 diagrams** total. Each diagram shows the services in the pattern and their state (color-coded) under that specific scenario. It reuses the **cached service names** from the context rather than re-extracting them.
11. By default, diagrams are **built programmatically** — no Gemini calls at all. A structured `STATE_MATRIX` maps every (strategy, phase) pair to the expected service states in Primary and DR regions. Each service is classified as "data" (databases, storage) or "compute" (everything else) and assigned the correct state (Active, Standby, Scaled-Down, Not-Deployed, Restoring, Syncing) from the matrix.
    - The **SVG** (embeddable in web pages) is templated in Python: two regions side-by-side, colour-coded service boxes, state labels, dashed cross-region arrows with mechanism labels, and a legend. Always-valid XML — no retry logic needed.
    - The **draw.io XML** is also templated in Python using the built-in `DRAWIO_SERVICE_ICONS` registry of 40+ AWS and GCP icon shapes. When an architect opens the file in draw.io, they see official AWS Lambda / Cloud SQL / etc. icons instead of plain rectangles. State-dependent colouring and opacity (50% for Not-Deployed / Scaled-Down) are applied automatically.
    - An **AI mode** (`use_ai_diagrams=True`) is available as an opt-in flag for more creative SVG layouts. When enabled, SVG generation uses Gemini (defaulting to `gemini-2.0-flash` for speed), while draw.io XML remains programmatic (the AI draw.io call was the largest source of token waste).
12. Each SVG is locally converted to a **PNG** fallback image (using `svglib` + `reportlab` on Windows, or `cairosvg` on Linux).
13. In programmatic mode, all 12 diagrams complete in **under 1 second** with zero AI calls. In AI mode, generation is parallelised with a Semaphore(6) cap and a 3-minute timeout per diagram — timeouts fall back to the programmatic builder automatically.
14. All three files per diagram (SVG, draw.io XML, PNG) are uploaded to a **GCS bucket** in parallel, organized by pattern name, strategy, and phase — e.g., `patterns/my-pattern/hadr-diagrams/warm-standby/failover.svg`. All uploads run in parallel with a 1-minute timeout each.
15. The diagram URLs are embedded directly into the HA/DR markdown sections as `![alt](png_url)` inline images and `[Edit in draw.io](drawio_url)` download links. At this point the URLs still point to GCS. The SequentialAgent's work is done — control returns to the Orchestrator with the complete document in the `WorkflowContext`.

---

## Phase 3 — "Human says 'Looks good' — start publishing the docs"

16. The Orchestrator extracts the final documentation — including all HA/DR sections with embedded diagram images — from the `WorkflowContext` and sends it back to the React SPA for the user to read. The pattern documentation and the HA/DR sections are shown in **collapsible expander panels** so they're easy to navigate.
17. If the user is happy, they click **"Approve & Continue."**
18. The app calls the Orchestrator's `approve_docs` task (passing the `workflow_id`). The Orchestrator saves the approval in the **AlloyDB database** and updates the workflow state to `CODE_GEN` so the user can resume from here if they close the browser.
19. The Orchestrator immediately kicks off a **background task** to publish the documentation to SharePoint (the company's knowledge base). It does *not* wait for this to finish — it moves on right away. During publishing, the `SharePointPublisher` processes each document section:
    - **Mermaid diagrams** (` ```mermaid ` blocks) are rendered to PNG via the Kroki service, uploaded to SharePoint Site Assets (`GeneratedDiagrams/` folder), and the markdown is rewritten with the SharePoint image URL.
    - **GCS-hosted HA/DR PNGs** (`![alt](https://storage.googleapis.com/…)`) are downloaded, uploaded to SharePoint Site Assets, and the markdown URL is rewritten — so diagrams render inline on the SharePoint page instead of depending on external GCS URLs. SVG view links and draw.io download links remain as GCS hyperlinks.
    - The processed markdown is then converted to HTML and assembled into SharePoint web parts.
    The background worker updates the database as it goes: first to "IN_PROGRESS", then to "COMPLETED" with the SharePoint page URL.

---

## Phase 4 — "Now build the actual code"

This phase uses **A2A HTTP calls** to communicate with the artifact agents, which run as separate services.

20. While docs are being published in the background, the Orchestrator starts code generation. First, it calls the **Component Specification Agent**.
21. This agent reads the documentation and extracts keywords (e.g., "Cloud SQL", "Cloud Run", "Load Balancer"). It normalizes them to standard names using an alias dictionary (e.g., "postgres" becomes `rds_instance`).
22. For each component, it does a **real-time lookup** to find the actual infrastructure schema:
    - **First**, it checks GitHub for matching Terraform modules (reads the `variables.tf` and `outputs.tf` files to understand what inputs/outputs the module expects).
    - **If not found** on GitHub, it falls back to AWS Service Catalog to find matching CloudFormation products.
23. The agent assembles all of this into a **structured dependency graph** — basically a map of "Component A depends on Component B" — sorted in the right order to build them.
24. Next, the **Artifact Generation Agent** takes this specification. It also fetches **"Golden Sample" templates** from a cloud storage bucket (GCS) — these are pre-approved infrastructure-as-code files that serve as examples of how the company wants things built.
25. Using the specification + golden samples + documentation, the agent generates a complete **Artifact Bundle**: Terraform files for infrastructure AND application boilerplate code — all in one pass so cross-references between components are correct.
26. The **Artifact Validation Agent** then checks the generated code against a **6-point checklist**: Is the syntax correct? Is everything included? Are the components wired together properly? Are there security issues? Does the boilerplate actually make sense? Does it follow best practices? It gives a score out of 100 and either PASS or NEEDS_REVISION.
27. If it fails, the critique goes back to the generator to fix the specific issues. This **generate → validate → fix loop** runs up to 3 times.

---

## Phase 5 — "Human says 'Code looks good' — publish it to GitHub"

28. The validated code bundle is shown to the user in the React SPA.
29. The user reviews the file structure and code. If they're satisfied, they click **"Approve & Publish."**
30. The Orchestrator saves the approval in AlloyDB, updates the workflow state to `PUBLISH`, and immediately kicks off another **background task** — this time to push the code to GitHub. It uses the GitHub REST API to create a new commit with all the generated files organized into folders:
    - `infrastructure/terraform/` for IaC templates
    - `src/{component_name}/` for application code
31. The Orchestrator does *not* wait for the GitHub push to finish. It immediately returns a response to the app with **two tracking IDs** — one for the docs publishing and one for the code publishing.

---

## Phase 6 — "Wait for everything to finish"

32. The React SPA's `PublishStep` component enters a **polling loop**: every 3 seconds, it asks the Orchestrator "Are we done yet?" by calling `get_publish_status` with those two tracking IDs and the `workflow_id`.
33. The Orchestrator checks the AlloyDB database and reports back the current status (e.g., "Docs: COMPLETED, Code: IN_PROGRESS").
34. Once both tasks show "COMPLETED," the app displays the final **SharePoint page URL** and **GitHub commit URL** to the user. The Orchestrator marks the workflow state as `COMPLETED` and deactivates the row in AlloyDB. The SPA clears the `engen_workflow_id` from `localStorage`. Done!

---

## What happens if something goes wrong?

- If any Phase 2 A2A agent call fails, the Orchestrator's client **retries up to 3 times** with linear backoff. Phase 1 steps run in-process, so there are no network failures to retry — any exception propagates immediately and the workflow reports the error.
- If artifact validation fails 3 times in a row, the workflow **stops and shows the errors** for manual intervention.
- If the background publishing to SharePoint or GitHub fails, the database status is set to **"FAILED"** and the polling UI shows an error message to the user.
- If the HA/DR text generation fails at any point inside the loop, it **does not stop the workflow**. The step catches the exception and inserts a placeholder message ("*HA/DR section generation failed. Please complete manually.*"). The main document is **never blocked** by HA/DR failures.
- If HA/DR diagram generation fails after the loop, the text documentation is still delivered intact.
- In programmatic diagram mode (default), there are no AI failures possible — diagrams are deterministic Python templates. In AI mode, if a single diagram takes too long (over 3 minutes), it **falls back to the programmatic builder** automatically.
- If the user closes the browser mid-workflow, the state is **already persisted** in AlloyDB at the last completed phase. Reopening the SPA will automatically resume from that point (Phase 0 above). No work is lost.

---

## Key performance characteristics

| Technique | What it does | Impact |
|---|---|---|
| In-process workflow execution | Phase 1 runs all steps in the same Python process — no HTTP, no JSON serialization, no timeouts | Eliminates network overhead entirely |
| Parallel HA/DR retrieval + donor extraction | `asyncio.gather` runs service HA/DR lookup and donor section extraction simultaneously | Saves ~5–10 seconds per iteration |
| Service name caching | Extracted once from the document and stored in context; reused by HA/DR text gen and diagram gen | Avoids redundant processing |
| Selective HA/DR regeneration | On loop iterations 2+, skips full HA/DR regen if the reviewer didn't critique that section | Saves ~30–60 seconds per skipped regeneration |
| Programmatic diagram generation | SVG + draw.io XML built from a structured state matrix — zero Gemini calls, 12 diagrams in < 1 second | Eliminates ~150 seconds and 24+ Gemini calls |
| HA/DR inside the review loop | Reviewer critiques the full document including HA/DR — catches HA/DR quality issues early | Reduces total iterations needed |
