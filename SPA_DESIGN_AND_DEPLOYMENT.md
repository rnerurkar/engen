# Pattern Factory UI — SPA Design & Deployment Guide

> **Version 1.2** — React 18 + Vite conversion of the Streamlit front-end.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Streamlit → React Mapping](#3-streamlit--react-mapping)
4. [Component Design](#4-component-design)
5. [State Management](#5-state-management)
6. [API Client Layer](#6-api-client-layer)
   - [6.1 BFF API Task Inventory](#61-bff-api-task-inventory)
7. [Deployment Option 1 — Local Development (VSCode Terminal)](#7-deployment-option-1--local-development-vscode-terminal)
8. [Deployment Option 2 — GCP Cloud Run](#8-deployment-option-2--gcp-cloud-run)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                   Browser (SPA)                  │
│  React 18 + Vite                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Sidebar  │ │ Chevron  │ │  Step Components  │  │
│  │ (Reset)  │ │ Stepper  │ │ Input ▸ DocReview │  │
│  │          │ │          │ │ CodeGen ▸ CodeRev │  │
│  │          │ │          │ │ ▸ Publish         │  │
│  └──────────┘ └──────────┘ └──────────────────┘  │
│        │              fetch("/api/invoke")        │
└────────┼─────────────────────────────────────────┘
         │  Vite proxy (dev) / nginx proxy (prod)
         ▼
┌──────────────────────────────────────────────────┐
│  Orchestrator Agent  (port 9000)                 │
│  POST /invoke  { task, payload }                 │
│  ┌─────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │Retriever│ │ Generator │ │ Publisher agents  │  │
│  └─────────┘ └───────────┘ └──────────────────┘  │
└──────────────────────────────────────────────────┘
```

The SPA communicates with the **same Orchestrator Agent** as the Streamlit app.
No backend code changes are required.

---

## 2. Project Structure

```
engen-ui/
├── index.html                  # HTML shell (Vite entry)
├── package.json                # Dependencies & scripts
├── vite.config.js              # Vite config + dev proxy
├── .env                        # Dev environment vars
├── .env.production             # Prod overrides
├── .gitignore
├── Dockerfile                  # Multi-stage build (node → nginx)
├── nginx.conf                  # Production nginx (SPA + API proxy)
├── cloudbuild.yaml             # Cloud Build → Artifact Registry → Cloud Run
└── src/
    ├── main.jsx                # ReactDOM entry
    ├── App.jsx                 # Root component — wizard state machine
    ├── index.css               # Global styles (CSS custom properties)
    ├── api/
    │   └── orchestrator.js     # fetch wrapper — callOrchestrator(task, payload)
    ├── components/
    │   ├── Collapsible.jsx     # Expander / accordion panel
    │   ├── ProgressBar.jsx     # Chevron stepper (active / completed / inactive states)
    │   ├── Sidebar.jsx         # Process controls (Reset)
    │   └── Spinner.jsx         # Inline loading indicator
    └── steps/
        ├── InputStep.jsx       # Step 1 — pattern name + diagram upload
        ├── DocReviewStep.jsx   # Step 2 — review & approve docs
        ├── CodeGenStep.jsx     # Step 3 — auto-trigger code generation
        ├── CodeReviewStep.jsx  # Step 4 — review & approve artifacts
        └── PublishStep.jsx     # Step 5 — poll publish status
```

---

## 3. Streamlit → React Mapping

| Streamlit Concept | React Equivalent | File |
|---|---|---|
| `st.session_state.step` | `useState("INPUT")` in App | `App.jsx` |
| `st.session_state.doc_data` | `useState(null)` — `docData` | `App.jsx` |
| `st.session_state.code_data` | `useState(null)` — `codeData` | `App.jsx` |
| `st.progress(idx/5)` | `<ProgressBar currentStep={step} />` (chevron stepper) | `ProgressBar.jsx` |
| `st.sidebar` + Reset button | `<Sidebar onReset={…} />` | `Sidebar.jsx` |
| `st.expander(…)` | `<Collapsible title={…}>` | `Collapsible.jsx` |
| `st.spinner(…)` | `<Spinner message={…} />` | `Spinner.jsx` |
| `st.text_input` / `st.file_uploader` | `<input type="text">` / `<input type="file">` | `InputStep.jsx` |
| `st.image(uploaded_file)` | `<img src={URL.createObjectURL(f)} />` | `InputStep.jsx` |
| `st.markdown(content)` | `<ReactMarkdown>{content}</ReactMarkdown>` | `DocReviewStep.jsx` |
| `st.json(artifacts)` | `<pre>{JSON.stringify(…, null, 2)}</pre>` | `CodeReviewStep.jsx` |
| `st.rerun()` | `setStep("NEXT_STATE")` — React re-renders automatically | `App.jsx` |
| `call_orchestrator()` (sync requests) | `callOrchestrator()` (async fetch) | `orchestrator.js` |
| `time.sleep(3)` polling loop | `setInterval` / `setTimeout` in `useEffect` | `PublishStep.jsx` |

---

## 4. Component Design

### 4.1 Shared Components

| Component | Purpose | Props |
|---|---|---|
| **ProgressBar** | Chevron stepper — active step highlighted in blue, completed in green, inactive dimmed at 50% opacity | `currentStep` |
| **Sidebar** | Left panel with "Reset Workflow" button | `onReset` |
| **Collapsible** | Expandable/collapsible content panel | `title`, `defaultOpen`, `children` |
| **Spinner** | CSS spinner + message | `message` |

### 4.2 Step Components

Each step component is **self-contained**: it owns its local UI state (loading flags, form fields) and communicates with the parent `App` via callback props.

| Step | Triggers | Outputs |
|---|---|---|
| **InputStep** | User clicks "Start Analysis" | Calls `onComplete(docData)` |
| **DocReviewStep** | User clicks "Approve & Publish" | Calls `onApprove()` |
| **CodeGenStep** | Auto-fires on mount (`useEffect`) | Calls `onComplete(codeData)` |
| **CodeReviewStep** | User clicks "Approve & Publish" | Calls `onApprove()` |
| **PublishStep** | Auto-polls on mount | Renders status cards |

---

## 5. State Management

The app uses **React `useState`** — no external state library is needed because the wizard is linear and all state is local.

```
App (root)
 ├── step      : "INPUT" | "DOC_REVIEW" | "CODE_GEN" | "CODE_REVIEW" | "PUBLISH"
 ├── docData   : object | null   (result of phase1_generate_docs)
 ├── codeData  : object | null   (result of phase2_generate_code)
 └── error     : string | null   (latest error message)
```

**Transitions** are driven by callbacks passed to each step component.  
`handleReset()` returns everything to initial state.

---

## 6. API Client Layer

[`src/api/orchestrator.js`](engen-ui/src/api/orchestrator.js)

```js
// POST { task, payload } → Orchestrator /invoke
export async function callOrchestrator(task, payload) { … }

// File → base64 (strips data URI prefix)
export function fileToBase64(file) { … }
```

**URL resolution:**

| Environment | `VITE_API_BASE_URL` | Actual target |
|---|---|---|
| Local dev | `/api` (default) | Vite proxy → `http://localhost:9000` |
| Production | Full URL or `/api` behind nginx | nginx proxy → Orchestrator service |

### 6.1 BFF API Task Inventory

All BFF APIs are exposed by a **single agent** — the **OrchestratorAgent** (port 9000). The React SPA communicates exclusively with the Orchestrator via `POST /invoke` with different `task` values. The Orchestrator then delegates to downstream agents via A2A.

| # | Task Name | Triggered By | SPA Step Transition | Purpose |
|---|-----------|-------------|---------------------|---------|
| 1 | `phase1_generate_docs` | "Start Analysis" button | `INPUT` → `DOC_REVIEW` | Upload diagram + title → returns generated doc sections, HA/DR text, HA/DR diagram URIs, `workflow_id` |
| 2 | `approve_docs` | "Approve & Continue" button | `DOC_REVIEW` → `CODE_GEN` | Saves approval in CloudSQL, fires-and-forgets SharePoint publish, advances workflow state |
| 3 | `phase2_generate_code` | Auto-triggered on step mount | `CODE_GEN` → `CODE_REVIEW` | Runs component spec → artifact gen → validation loop, returns artifacts + spec |
| 4 | `approve_code` | "Approve & Publish" button | `CODE_REVIEW` → `PUBLISH` | Saves approval, fires-and-forgets GitHub publish, advances workflow state |
| 5 | `get_publish_status` | 3-second polling interval | `PUBLISH` | Returns doc/code publish status per `review_id`, marks workflow `COMPLETED` when both done |
| 6 | `resume_workflow` | `useEffect` on App mount | Any (resume) | Loads persisted workflow state from CloudSQL, returns step + all accumulated data |
| 7 | `list_workflows` | Resume picker UI (future) | Pre-INPUT | Lists up to 10 active workflows for a user |
| 8 | `start_workflow` | Legacy / unused | — | Legacy loop entry point (returns error directing to phase-based flow) |

```
SPA                          Orchestrator (port 9000)              Downstream Agents
 │                                │                                     │
 ├─ POST /invoke ────────────────►│                                     │
 │  { "task": "phase1_...",       │                                     │
 │    "payload": { title, b64 }}  │── A2A ──► GeneratorAgent (9002)     │
 │                                │── A2A ──► RetrieverAgent (9001)     │
 │                                │── A2A ──► ReviewerAgent (9003)      │
 │                                │── A2A ──► HADRRetrieverAgent (9006) │
 │                                │── A2A ──► HADRGeneratorAgent (9007) │
 │                                │── A2A ──► HADRDiagramGenAgent (9008)│
 │◄─ { status, result: {         │                                     │
 │     workflow_id, sections,     │                                     │
 │     full_doc, hadr_... }}      │                                     │
 │                                │                                     │
 ├─ POST /invoke ────────────────►│                                     │
 │  { "task": "resume_workflow",  │── SQL ──► CloudSQL workflow_state   │
 │    "payload": { workflow_id }} │                                     │
 │◄─ { found, step, doc_data,    │                                     │
 │     code_data, ... }           │                                     │
```

**Why a single BFF endpoint?** The Orchestrator acts as a facade — the SPA never communicates directly with the 7 downstream agents (ports 9001–9008). This provides a single CORS origin, a single auth boundary, task-based routing without REST resource design, centralized workflow state ownership, and deployment simplicity (one public-facing Cloud Run service).

---

## 7. Deployment Option 1 — Local Development (VSCode Terminal)

### Prerequisites

| Requirement | Version |
|---|---|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Orchestrator Agent | Running on `localhost:9000` |

### Steps

1. **Open a terminal in VSCode** (`Ctrl+`` ` or Terminal → New Terminal).

2. **Navigate to the UI folder:**

   ```powershell
   cd engen-ui
   ```

3. **Install dependencies:**

   ```powershell
   npm install
   ```

4. **Start the dev server:**

   ```powershell
   npm run dev
   ```

   Vite will start on **http://localhost:3000**.  
   The dev proxy automatically forwards `/api/*` to `http://localhost:9000/*`.

5. **Open the browser** — navigate to `http://localhost:3000`.

6. **Hot Module Replacement (HMR)** — save any `.jsx` or `.css` file and the browser updates instantly without a full page reload.

### Troubleshooting

| Issue | Fix |
|---|---|
| `EACCES` / port in use | Change `server.port` in `vite.config.js` |
| API calls fail with 502 | Ensure Orchestrator is running on port 9000 |
| Node version too old | Install Node 18+ via `nvm install 18` |

---

## 8. Deployment Option 2 — GCP Cloud Run

### Architecture

```
Cloud Build
   │  (trigger on git push or manual)
   ▼
Artifact Registry            Cloud Run (engen-ui)
   engen-ui:abc123  ──────▶  nginx:8080
                               ├── /         → static SPA
                               └── /api/*    → Orchestrator Cloud Run
```

### Prerequisites

| Requirement | Details |
|---|---|
| GCP Project | Active project with billing enabled |
| `gcloud` CLI | Installed & authenticated (`gcloud auth login`) |
| APIs enabled | Cloud Run, Cloud Build, Artifact Registry |
| Orchestrator deployed | Already on Cloud Run or accessible endpoint |

### Step-by-step

#### A. One-time setup

```bash
# Set variables
export PROJECT_ID=your-project-id
export REGION=us-central1
export REPO=engen

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Create Artifact Registry repo (if not exists)
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID
```

#### B. Build & deploy (manual)

```bash
cd engen-ui

# Build the container image
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/engen-ui:latest \
  --project=$PROJECT_ID

# Deploy to Cloud Run
gcloud run deploy engen-ui \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/engen-ui:latest \
  --region $REGION \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --project=$PROJECT_ID
```

#### C. Automated CI/CD (Cloud Build trigger)

The included [`cloudbuild.yaml`](engen-ui/cloudbuild.yaml) automates build → push → deploy.

```bash
# Create a push trigger on main branch
gcloud builds triggers create github \
  --name=engen-ui-deploy \
  --repo-name=engen \
  --repo-owner=rnerurkar \
  --branch-pattern="^main$" \
  --build-config=engen-ui/cloudbuild.yaml \
  --project=$PROJECT_ID
```

#### D. Connect to Orchestrator

Update `nginx.conf` so the `/api/` proxy points to your deployed Orchestrator:

```nginx
location /api/ {
    proxy_pass https://orchestrator-xyz.a.run.app/;
    proxy_http_version 1.1;
    proxy_set_header Host orchestrator-xyz.a.run.app;
    proxy_read_timeout 600s;
}
```

Or set `VITE_API_BASE_URL` to the Orchestrator URL at build time (client-side fetch, requires CORS on the Orchestrator).

#### E. Verify

```bash
# Get the Cloud Run URL
gcloud run services describe engen-ui \
  --region $REGION \
  --format "value(status.url)" \
  --project=$PROJECT_ID
```

Open the returned URL in a browser — the SPA should load and connect to the Orchestrator.

---

## Summary

| Aspect | Detail |
|---|---|
| Framework | React 18 + Vite 6 |
| State | `useState` (no Redux needed) |
| Styling | Vanilla CSS with custom properties |
| API layer | `fetch` wrapper with Vite proxy (dev) / nginx proxy (prod) |
| Local run | `npm install` → `npm run dev` → http://localhost:3000 |
| GCP deploy | Docker → nginx → Cloud Run (port 8080) |
| CI/CD | Cloud Build trigger with `cloudbuild.yaml` |
