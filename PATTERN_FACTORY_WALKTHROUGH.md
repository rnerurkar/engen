# The Pattern Factory Workflow — A Plain English Walkthrough (v2.4)

Think of Pattern Factory as an assembly line with **8 phases**. A user uploads an architecture diagram, and the system generates documentation (including HA/DR sections with visual diagrams) and deployable code for it — with human checkpoints along the way.

The front-end is a **React 18 + Vite single-page application (SPA)** that replaced the earlier Streamlit prototype. It presents a 5-step chevron-style wizard (Input → Doc Review → Code Gen → Code Review → Publish) and communicates with the Orchestrator via a single `POST /invoke` BFF endpoint. Workflow state is persisted to **CloudSQL** so users can close the browser and resume later.

---

## Phase 0 — "Resume where you left off" (automatic)

Before anything else, the SPA checks whether the user has an in-progress workflow.

0a. When the React app loads, a `useEffect` hook reads `localStorage` for a saved `engen_workflow_id`.
0b. If found, the app calls the Orchestrator's `resume_workflow` task with that ID. The Orchestrator loads the full workflow snapshot from the **CloudSQL `workflow_state` table** — including the current phase, saved documentation, and any generated code.
0c. The app restores `step`, `docData`, and `codeData` from the server response and jumps the user straight to the step where they left off. A loading spinner is shown while resuming.
0d. If the workflow is no longer active (completed or deleted), the localStorage key is cleared and the user starts fresh.

---

## Phase 1 — "Look at the picture and find something similar"

1. The user opens the **Pattern Factory SPA** (a React + Vite single-page application), uploads an architecture diagram image (e.g., a PNG of a cloud architecture), and types in a title. The UI shows a chevron-style stepper at the top to indicate progress through the 5-step wizard.
2. The app sends this to the **Orchestrator** — the "traffic controller" that runs the whole show. The Orchestrator creates a new row in the CloudSQL `workflow_state` table and returns a `workflow_id` that the SPA stores in `localStorage` for future resume.
3. The Orchestrator passes the image to the **Vision Agent** (powered by Gemini Vision AI). This agent looks at the picture and writes a plain-text technical description of what it sees (e.g., "A Cloud Run service connected to a Cloud SQL database behind a load balancer").
4. The Orchestrator takes that description and sends it to the **Retrieval Agent**. This agent searches a knowledge base (Vertex AI Search) for the closest matching existing design pattern — called a **"Donor Pattern."** Think of it like finding a similar recipe before writing a new one.

---

## Phase 2 — "Write the documentation, then get it reviewed"

5. Now the Orchestrator has two things: the image description and the donor pattern. It sends both to the **Generator Agent**, which uses Gemini Pro to write a first draft of documentation sections (Problem Statement, Solution, Architecture, etc.).
6. That draft goes to the **Reviewer Agent** — an AI "critic." It scores the draft against quality guidelines and returns specific feedback (e.g., "The security section is too vague").
7. If the score isn't good enough, the Orchestrator sends the critique back to the Generator to revise. This **generate → review → revise loop** runs up to 3 times until the quality is acceptable.

---

## Phase 2b — "Write the HA/DR sections for every disaster recovery strategy"

This step runs right after the documentation loop finishes. It's wrapped in a safety net — if anything here fails, the main document still gets delivered with a placeholder message saying "HA/DR section generation failed. Please complete manually." The main document is **never blocked** by HA/DR failures.

Just like the Generator Agent, Retriever Agent, and Reviewer Agent, the HA/DR components are now proper **agents** — each running as its own HTTP service and accessed by the Orchestrator via **A2A (Agent-to-Agent) HTTP calls**. This keeps the architecture consistent: the Orchestrator never directly imports HA/DR code; it delegates everything over the network.

8. The Orchestrator scans the draft documentation and picks out all the cloud service names it can find (e.g., "Amazon RDS", "AWS Lambda", "Cloud Run"). It does this by matching words against a dictionary of 40+ known service aliases and a curated list of common AWS and GCP service names.
9. For each service found, the Orchestrator calls the **HA/DR Retriever Agent** (port 9006) via A2A HTTP. Inside that agent, the `ServiceHADRRetriever` searches a dedicated HA/DR knowledge base (a separate Vertex AI Search data store) to pull back reference documentation about how that service behaves during disasters. It searches for every combination of *service × DR strategy* (e.g., "How does Amazon RDS behave during a Warm Standby failover?"). All of these searches — typically 16 to 32 queries — run **in parallel at the same time** rather than one-by-one, which is much faster.
10. The Orchestrator also calls the **HA/DR Generator Agent** (port 9007) via A2A HTTP to extract the donor pattern's existing HA/DR sections. This is used as a stylistic template (a "one-shot example") so the new content matches the company's standard format.
11. The Orchestrator then calls the **HA/DR Generator Agent** again (same port 9007) to write four separate HA/DR sections — one per DR strategy (Backup and Restore, Pilot Light On Demand, Pilot Light Cold Standby, Warm Standby). Inside the agent, all four sections are generated **in parallel** (each with a 2-minute timeout) rather than sequentially. Each section includes sub-sections for Initial Provisioning, Failover, and Failback, with summary tables showing each service's state (Active, Standby, Scaled-Down, or Not-Deployed).

---

## Phase 2c — "Generate visual HA/DR diagrams for every scenario"

This step also runs with the same safety net as Phase 2b — if diagrams fail, the text documentation still gets delivered.

12. The Orchestrator makes a single A2A HTTP call to the **HA/DR Diagram Generator Agent** (port 9008). This agent handles both diagram generation and cloud storage upload internally. Inside the agent, the `HADRDiagramGenerator` creates component diagrams for every combination of DR strategy × lifecycle phase: 4 strategies × 3 phases = **12 diagrams** total. Each diagram shows the services in the pattern and their state (color-coded) under that specific scenario.
13. For each diagram, the agent makes **two AI calls** to Gemini 1.5 Pro:
    - One to generate an **SVG** image (embeddable in web pages).
    - One to generate a **draw.io XML** file (editable by architects in the draw.io tool). The draw.io diagrams use **official AWS and GCP icon shapes** from a built-in registry of 40+ cloud services — so when you open them in draw.io, you see the actual AWS Lambda icon or Cloud SQL icon instead of plain rectangles.
14. Each SVG is also locally converted to a **PNG** fallback image (using `svglib` + `reportlab` on Windows, or `cairosvg` on Linux).
15. All 12 diagram generations run **in parallel**, but capped at 4 at a time (to avoid hitting Gemini's rate limits). Each diagram gets a 3-minute timeout — if it takes too long, a simpler fallback diagram is created automatically without AI.
16. Still inside the same agent, the `HADRDiagramStorage` component uploads all three files per diagram (SVG, draw.io XML, PNG) to a **GCS bucket**, organized by pattern name, strategy, and phase — e.g., `patterns/my-pattern/hadr-diagrams/warm-standby/failover.svg`. All uploads run in parallel with a 1-minute timeout each.
17. The agent returns the diagram URLs back to the Orchestrator. Since JSON can't handle Python tuple keys like `("Warm Standby", "Failover")`, the agent uses string keys like `"Warm Standby|Failover"` — the Orchestrator splits them back into tuples. The resulting diagram URLs are embedded directly into the HA/DR markdown sections, so the final documentation includes inline images and download links for the editable draw.io files.

---

## Phase 3 — "Human says 'Looks good' — start publishing the docs"

18. The Orchestrator sends the final documentation — including all HA/DR sections with embedded diagram images — back to the React SPA for the user to read. The pattern documentation and the HA/DR sections are shown in **collapsible expander panels** so they're easy to navigate.
19. If the user is happy, they click **"Approve & Continue."**
20. The app calls the Orchestrator's `approve_docs` task (passing the `workflow_id`). The Orchestrator saves the approval in the **CloudSQL database** and updates the workflow state to `CODE_GEN` so the user can resume from here if they close the browser.
21. The Orchestrator immediately kicks off a **background task** to publish the documentation to SharePoint (the company's knowledge base). It does *not* wait for this to finish — it moves on right away. The background worker updates the database as it goes: first to "IN_PROGRESS", then to "COMPLETED" with the SharePoint page URL.

---

## Phase 4 — "Now build the actual code"

22. While docs are being published in the background, the Orchestrator starts code generation. First, it calls the **Component Specification Agent**.
23. This agent reads the documentation and extracts keywords (e.g., "Cloud SQL", "Cloud Run", "Load Balancer"). It normalizes them to standard names using an alias dictionary (e.g., "postgres" becomes `rds_instance`).
24. For each component, it does a **real-time lookup** to find the actual infrastructure schema:
    - **First**, it checks GitHub for matching Terraform modules (reads the `variables.tf` and `outputs.tf` files to understand what inputs/outputs the module expects).
    - **If not found** on GitHub, it falls back to AWS Service Catalog to find matching CloudFormation products.
25. The agent assembles all of this into a **structured dependency graph** — basically a map of "Component A depends on Component B" — sorted in the right order to build them.
26. Next, the **Artifact Generation Agent** takes this specification. It also fetches **"Golden Sample" templates** from a cloud storage bucket (GCS) — these are pre-approved infrastructure-as-code files that serve as examples of how the company wants things built.
27. Using the specification + golden samples + documentation, the agent generates a complete **Artifact Bundle**: Terraform files for infrastructure AND application boilerplate code — all in one pass so cross-references between components are correct.
28. The **Artifact Validation Agent** then checks the generated code against a **6-point checklist**: Is the syntax correct? Is everything included? Are the components wired together properly? Are there security issues? Does the boilerplate actually make sense? Does it follow best practices? It gives a score out of 100 and either PASS or NEEDS_REVISION.
29. If it fails, the critique goes back to the generator to fix the specific issues. This **generate → validate → fix loop** runs up to 3 times.

---

## Phase 5 — "Human says 'Code looks good' — publish it to GitHub"

30. The validated code bundle is shown to the user in the React SPA.
31. The user reviews the file structure and code. If they're satisfied, they click **"Approve & Publish."**
32. The Orchestrator saves the approval in CloudSQL, updates the workflow state to `PUBLISH`, and immediately kicks off another **background task** — this time to push the code to GitHub. It uses the GitHub REST API to create a new commit with all the generated files organized into folders:
    - `infrastructure/terraform/` for IaC templates
    - `src/{component_name}/` for application code
33. The Orchestrator does *not* wait for the GitHub push to finish. It immediately returns a response to the app with **two tracking IDs** — one for the docs publishing and one for the code publishing.

---

## Phase 6 — "Wait for everything to finish"

34. The React SPA's `PublishStep` component enters a **polling loop**: every 3 seconds, it asks the Orchestrator "Are we done yet?" by calling `get_publish_status` with those two tracking IDs and the `workflow_id`.
35. The Orchestrator checks the CloudSQL database and reports back the current status (e.g., "Docs: COMPLETED, Code: IN_PROGRESS").
36. Once both tasks show "COMPLETED," the app displays the final **SharePoint page URL** and **GitHub commit URL** to the user. The Orchestrator marks the workflow state as `COMPLETED` and deactivates the row in CloudSQL. The SPA clears the `engen_workflow_id` from `localStorage`. Done!

---

## What happens if something goes wrong?

- If any agent call fails, the Orchestrator **retries up to 3 times**.
- If artifact validation fails 3 times in a row, the workflow **stops and shows the errors** for manual intervention.
- If the background publishing to SharePoint or GitHub fails, the database status is set to **"FAILED"** and the polling UI shows an error message to the user.
- If the HA/DR text generation or diagram generation fails at any point, the system **does not stop**. It inserts a placeholder message ("*HA/DR section generation failed. Please complete manually.*") and continues with the rest of the document. The main pattern documentation is never blocked by HA/DR failures.
- If a single HA/DR diagram takes too long (over 3 minutes), it **times out gracefully** and a simpler fallback diagram is generated automatically without AI calls.
- If the user closes the browser mid-workflow, the state is **already persisted** in CloudSQL at the last completed phase. Reopening the SPA will automatically resume from that point (Phase 0 above). No work is lost.
