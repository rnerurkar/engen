# EnGen: Architecture Pattern Documentation & Artifact Generation

**Version:** 2.0  
**Date:** April 2026

EnGen is an AI-powered system that automates the creation of architecture documentation and Infrastructure as Code (IaC) artifacts by analysing architecture diagrams and leveraging existing patterns.

## Overview

EnGen uses a two-plane architecture:

1. **Ingestion Plane** — Extracts and indexes architecture patterns from SharePoint into a GCP-based knowledge graph (Vertex AI Search, GCS)
2. **Inference Plane** — A single orchestrator process runs two ADK workflow pipelines that analyse diagrams, generate documentation, and produce IaC artifacts

## Key Features

- **Automated Documentation** — Generate architecture documentation from diagrams with minimal human intervention
- **Knowledge Reuse** — Leverage existing donor patterns for consistency and quality
- **HA/DR Coverage** — Automated HA/DR documentation across 4 DR strategies x 3 lifecycle phases with programmatic diagrams (SVG, draw.io XML, PNG)
- **IaC Artifact Generation** — Produce Terraform / CloudFormation templates and application boilerplate from approved documentation
- **Quality Assurance** — Iterative refinement loops with automated review and validation
- **Resumable Workflows** — AlloyDB-backed state persistence for browser/session recovery
- **Publishing** — Fire-and-forget publishing to SharePoint (docs) and GitHub (code)

## Architecture

### Ingestion Service
- **SharePoint Integration** — OAuth authentication, page extraction, image download
- **Vertex AI Search Pipeline** — Document chunks with metadata ingested into Discovery Engine
- **Service HA/DR Pipeline** — Per-service HA/DR documentation with diagram extraction
- **GCP Stack** — Vertex AI, Discovery Engine, Cloud Storage

### Inference Service — ADK Workflow Architecture

All agents run **in-process** via ADK `SequentialAgent` and `LoopAgent` — no HTTP/A2A overhead, no inter-service serialisation, no timeout issues.

**Phase 1 — Document Generation:**
```
Phase1DocGenerationWorkflow (SequentialAgent)
  ├─ VisionAnalysisStep       — Gemini Vision image description
  ├─ DonorRetrievalStep       — Vertex AI Search donor lookup
  ├─ ContentRefinementLoop (LoopAgent, max 3, exit_key="approved")
  │    ├─ PatternGenerateStep  — core doc generation (Gemini Pro)
  │    ├─ HADRSectionsStep     — HA/DR retrieval + generation (parallel)
  │    └─ FullDocReviewStep    — reviews full doc incl. HA/DR
  └─ HADRDiagramStep           — async diagram gen + GCS upload
```

**Phase 2 — Artifact Generation:**
```
Phase2ArtifactWorkflow (SequentialAgent)
  ├─ ComponentSpecStep         — extract component spec from docs
  └─ ArtifactRefinementLoop (LoopAgent, max 3, exit_key="validation_passed")
       ├─ ArtifactGenerateStep — generate IaC + boilerplate
       └─ ArtifactValidateStep — validate against quality rubric
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `core/generator.py` | Pattern documentation generation via Gemini Pro |
| `core/retriever.py` | Vertex AI Search donor pattern retrieval |
| `core/reviewer.py` | Automated document quality review |
| `core/pattern_synthesis/component_specification.py` | Real-time component spec extraction (GitHub + Service Catalog) |
| `core/pattern_synthesis/artifact_generator.py` | IaC / boilerplate generation with golden samples |
| `core/pattern_synthesis/artifact_validator.py` | Artifact validation against quality rubric |
| `core/pattern_synthesis/hadr_generator.py` | HA/DR documentation generation (4 strategies) |
| `core/pattern_synthesis/hadr_diagram_generator.py` | Programmatic SVG + draw.io + PNG diagram generation |
| `core/pattern_synthesis/hadr_diagram_storage.py` | GCS upload for diagram bundles |
| `core/pattern_synthesis/service_hadr_retriever.py` | Per-service HA/DR retrieval from Vertex AI Search |

### Support Libraries

| Module | Purpose |
|--------|---------|
| `lib/adk_core.py` | ADK framework: `ADKAgent`, `WorkflowAgent`, `SequentialAgent`, `LoopAgent`, `WorkflowContext` |
| `lib/sharepoint_publisher.py` | SharePoint modern page publishing with diagram re-hosting |
| `lib/github_publisher.py` | GitHub repository code publishing via MCP |
| `lib/cloudsql_client.py` | AlloyDB connection management |
| `lib/workflow_state.py` | Resumable workflow state persistence |
| `lib/component_sources.py` | Component type aliases and normalisation |
| `lib/github_mcp_client.py` | GitHub MCP / PyGithub Terraform module lookup |
| `lib/service_catalog_client.py` | AWS Service Catalog product lookup |
| `lib/visualizer.py` | Diagram rendering utilities |

## Quick Start

### Prerequisites
- Python 3.13+
- Google Cloud Platform account with Vertex AI enabled
- SharePoint access with appropriate credentials

### Installation

```bash
git clone https://github.com/rnerurkar/engen.git
cd engen

# Install inference service dependencies
cd inference-service
pip install -r requirements.txt
```

### Configuration

```bash
# GCP
export GCP_PROJECT_ID="your-project-id"
export GCP_LOCATION="us-central1"

# Vertex AI Search
export VERTEX_DATA_STORE_ID="your-datastore-id"
export SERVICE_HADR_DS_ID="your-hadr-datastore-id"

# AlloyDB
export ALLOYDB_INSTANCE="projects/.../instances/..."
export DB_USER="postgres"
export DB_PASS="your-password"

# SharePoint (for publishing)
export SHAREPOINT_TENANT_ID="your-tenant-id"
export SHAREPOINT_CLIENT_ID="your-client-id"
export SHAREPOINT_CLIENT_SECRET="your-secret"
export SHAREPOINT_SITE_ID="your-site-id"
```

### Running

```bash
# Inference service (single process — all agents in-process)
cd inference-service
python agents/orchestrator/main.py

# Streamlit UI (optional)
streamlit run streamlit_app.py
```

## Project Structure

```
engen/
├── README.md
├── DESIGN_DOCUMENT.md                  # Complete architecture documentation
├── PATTERN_FACTORY_WALKTHROUGH.md      # End-to-end walkthrough
├── inference-service/
│   ├── config.py                       # Configuration
│   ├── streamlit_app.py                # Streamlit UI
│   ├── agents/
│   │   └── orchestrator/
│   │       ├── main.py                 # OrchestratorAgent entry point
│   │       └── workflow_agents.py      # Phase 1 + Phase 2 workflow steps
│   ├── core/
│   │   ├── generator.py               # Pattern generation
│   │   ├── retriever.py               # Donor retrieval
│   │   ├── reviewer.py                # Quality review
│   │   └── pattern_synthesis/
│   │       ├── component_specification.py
│   │       ├── artifact_generator.py
│   │       ├── artifact_validator.py
│   │       ├── hadr_generator.py
│   │       ├── hadr_diagram_generator.py
│   │       ├── hadr_diagram_storage.py
│   │       └── service_hadr_retriever.py
│   └── lib/
│       ├── adk_core.py                 # ADK framework
│       ├── sharepoint_publisher.py     # SharePoint publishing
│       ├── github_publisher.py         # GitHub code publishing
│       ├── cloudsql_client.py          # AlloyDB client
│       ├── workflow_state.py           # Workflow state persistence
│       ├── component_sources.py        # Component type mappings
│       ├── github_mcp_client.py        # GitHub Terraform lookups
│       ├── service_catalog_client.py   # AWS Service Catalog lookups
│       └── visualizer.py              # Diagram rendering
├── ingestion-service/
│   ├── config.py
│   ├── clients/
│   │   └── sharepoint.py
│   └── pipelines/
│       ├── vertex_search_pipeline.py
│       └── service_hadr_pipeline.py
└── engen-ui/                           # SPA frontend (Vite + React)
    ├── src/
    │   ├── App.jsx
    │   └── api/orchestrator.js
    └── package.json
```

## Technology Stack

- **Language:** Python 3.13
- **AI/ML:** Vertex AI (Gemini 1.5 Pro, Discovery Engine)
- **Workflow:** ADK SequentialAgent / LoopAgent (in-process)
- **Data Storage:** AlloyDB, Cloud Storage
- **API Framework:** FastAPI + Uvicorn
- **Frontend:** React + Vite (SPA), Streamlit (dev UI)
- **Publishing:** SharePoint (MSAL), GitHub (MCP / PyGithub)

## Documentation

- [Design Document](DESIGN_DOCUMENT.md) — Complete system architecture
- [Pattern Factory Walkthrough](PATTERN_FACTORY_WALKTHROUGH.md) — End-to-end workflow walkthrough
- [SPA Design & Deployment](SPA_DESIGN_AND_DEPLOYMENT.md) — Frontend architecture
- [Ingestion Pipelines Walkthrough](INGESTION_PIPELINES_WALKTHROUGH.md) — Data ingestion details
- [Deployment Guide](DEPLOYMENT_GUIDE.md) — Cloud Run deployment instructions

## Repository

**GitHub:** https://github.com/rnerurkar/engen  
**Branch:** main
