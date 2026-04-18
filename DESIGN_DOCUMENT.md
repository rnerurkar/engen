# EnGen: Architecture Pattern Documentation System

**Document Version:** 4.0  
**Date:** April 15, 2026  
**Author:** EnGen Development Team  
**Status:** Production Ready

---

## 1. Objective

EnGen is an intelligent system that automates the creation of high-quality architecture documentation by leveraging a two-part approach:

1. **Ingestion Plane**: Extracts and indexes architecture patterns from SharePoint into a GCP-based knowledge graph
2. **Service HA/DR Ingestion**: Ingests service-level High Availability and Disaster Recovery documentation into a dedicated data store with structured metadata for precise filtered retrieval
3. **Serving Plane**: Uses an ADK workflow agent system to analyze new architecture diagrams and generate comprehensive documentation — including HA/DR sections — using relevant donor patterns
4. **Real-Time Component Resolution**: Queries live infrastructure sources (GitHub repositories via MCP and AWS Service Catalog) to ground generated artifacts in actual schemas

### Primary Goals

- **Automated Documentation**: Generate architecture documentation from diagrams with minimal human intervention
- **Knowledge Reuse**: Leverage existing architecture patterns to ensure consistency and quality
- **Scalability**: Handle large volumes of patterns and concurrent documentation requests
- **Quality Assurance**: Multi-agent review and refinement for production-grade output
- **HA/DR Documentation**: Automated generation of High Availability and Disaster Recovery sections grounded in service-level reference documentation

---

## 2. High-Level Component Diagram

This diagram represents the concrete implementation of the EnGen system, detailing the workflow agents involved in the pipeline.

```mermaid
graph TB
    subgraph ClientLayer["Client Layer"]
        UI[React SPA<br/>Vite + Chevron Wizard]
    end

    subgraph Serving["SERVING PLANE (Single-Process ADK Workflow)"]
        Orch[Orchestrator Agent<br/>- Workflow Coordinator]
        
        subgraph Phase1["Phase 1: Doc Generation (SequentialAgent)"]
            VA[VisionAnalysisStep<br/>- Gemini Vision]
            DR[DonorRetrievalStep<br/>- Vertex AI Search]
            subgraph Loop1["LoopAgent: ContentRefinementLoop (max 3)"]
                PG[PatternGenerateStep<br/>- Gemini Pro]
                HS[HADRSectionsStep<br/>- Parallel Retrieval]
                FDR[FullDocReviewStep<br/>- Quality Control]
            end
            HD[HADRDiagramStep<br/>- Programmatic SVG + draw.io + GCS]
            VA --> DR --> Loop1 --> HD
            PG --> HS --> FDR
        end

        subgraph Phase2["Phase 2: Artifact Generation (SequentialAgent)"]
            CompSpec[ComponentSpecStep<br/>- Real-Time Schema Resolution]
            subgraph Loop2["LoopAgent: ArtifactRefinementLoop (max 3)"]
                ArtGen[ArtifactGenerateStep<br/>- Golden Samples + Gemini]
                ArtVal[ArtifactValidateStep<br/>- 6-Point Rubric]
            end
            CompSpec --> Loop2
            ArtGen --> ArtVal
        end
        
        Orch -->|WorkflowContext| Phase1
        Orch -->|WorkflowContext| Phase2
    end

    subgraph RealTimeSources["Real-Time Component Sources"]
        GitHubMCP[GitHub MCP Server<br/>Terraform Modules]
        AWSSC[AWS Service Catalog<br/>CloudFormation Products]
    end

    subgraph Async["Async Workers"]
        PubDocs[SharePoint<br/>Publisher]
        PubCode[GitHub<br/>Publisher]
    end
    
    subgraph State["State Management"]
        DB[(AlloyDB<br/>Job Status)]
        WFS[(AlloyDB<br/>Workflow State)]
    end

    subgraph Ingestion["INGESTION PLANE (Managed Pipelines)"]
        SP[SharePoint Client]
        SPPipe[SharePoint<br/>Pipeline]
        VertexAI[Vertex AI<br/>Discovery Engine]
        HADRPipe[Service HA/DR<br/>Pipeline]
        HADRDS[HA/DR Data Store<br/>Vertex AI Search]
        
        SP --> SPPipe
        SP --> HADRPipe
        SPPipe --> VertexAI
        HADRPipe --> HADRDS
    end

    subgraph DiagramStorage["Diagram Artefacts"]
        DiagGCS[GCS Bucket<br/>hadr-diagrams]
    end
    
    HS -->|Direct Call| HADRDS
    HD -->|SVG + draw.io + PNG + Upload| DiagGCS

    UI --> Orch
    UI -.->|Poll via Orch| DB
    UI -.->|Resume via Orch| WFS
    Orch -->|Save Phase| WFS
    Orch -->|Fire & Forget| PubDocs
    Orch -->|Fire & Forget| PubCode
    CompSpec -->|Real-Time Lookup| GitHubMCP
    CompSpec -->|Fallback Lookup| AWSSC
    PubDocs --> DB
    PubCode --> DB
```

### 2.1 Agent Responsibilities

| Agent Name | Role | Primary Responsibility |
|------------|------|------------------------|
| **OrchestratorAgent** | Controller | Manages the end-to-end workflow via task-based BFF endpoints (`phase1_generate_docs`, `approve_docs`, `phase2_generate_code`, `approve_code`, `get_publish_status`, `resume_workflow`, `list_workflows`). Both Phase 1 (doc generation) and Phase 2 (artifact generation) are orchestrated entirely in-process using ADK `SequentialAgent` + `LoopAgent` primitives — no HTTP calls between agents. Core logic modules are instantiated directly and shared across workflow steps via a `WorkflowContext`. Persists workflow state to AlloyDB via `WorkflowStateManager` at every phase transition for resumable sessions. |
| **VisionAnalysisStep** | Analyser | ADK `WorkflowAgent` step that uses Gemini Vision (via `PatternGenerator.generate_search_description`) to produce a textual description of the architecture diagram. Runs in-process within the Phase 1 `SequentialAgent`. |
| **DonorRetrievalStep** | Librarian | ADK `WorkflowAgent` step that performs hybrid search in Vertex AI Search (via `VertexRetriever.get_best_donor_pattern`) to find the best donor pattern. Runs in-process within the Phase 1 `SequentialAgent`. |
| **PatternGenerateStep** | Creator | ADK `WorkflowAgent` step inside the Phase 1 `LoopAgent` that uses Gemini Pro (via `PatternGenerator.generate_pattern`) to generate core documentation sections, incorporating any critique from the reviewer on subsequent iterations. |
| **HADRSectionsStep** | HA/DR Writer | ADK `WorkflowAgent` step inside the Phase 1 `LoopAgent` that generates pattern-level HA/DR sections. Runs service HA/DR retrieval and donor extraction in parallel via `asyncio.gather`, caches service names across iterations, and skips HA/DR regeneration on iterations > 1 if the reviewer did not flag the HA/DR section. |
| **FullDocReviewStep** | Critic | ADK `WorkflowAgent` step inside the Phase 1 `LoopAgent` that reviews the **entire** document — including HA/DR sections — against quality rubrics and sets the `approved` flag. The reviewer critiques HA/DR quality, enabling HA/DR refinement within the loop. |
| **HADRDiagramStep** | HA/DR Visualiser & Storage | ADK `WorkflowAgent` step that runs **after** the Phase 1 `LoopAgent` to produce SVG, draw.io XML (with official AWS/GCP icon shapes), and PNG fallback images for every DR strategy × lifecycle phase combination. Diagrams are generated programmatically from a structured `STATE_MATRIX` — zero Gemini calls, 12 diagrams in < 1 second. An opt-in AI mode (`use_ai_diagrams=True`, defaults to `gemini-2.0-flash`) is available for creative SVG layouts; draw.io XML is always programmatic. Uploads all artefacts to GCS and embeds URLs into the HA/DR sections. |
| **ComponentSpecStep** | Architect | ADK `WorkflowAgent` step in the Phase 2 `SequentialAgent` that performs **real-time** lookups against GitHub repositories (via MCP Server or PyGithub fallback) and AWS Service Catalog to extract a structured dependency graph grounded in actual infrastructure schemas. Uses `component_sources.py` for type normalization. |
| **ArtifactGenerateStep** | Engineer | ADK `WorkflowAgent` step inside the Phase 2 `LoopAgent` that synthesizes IaC and Boilerplate using "Golden Sample" templates fetched from GCS. |
| **ArtifactValidateStep** | QA | ADK `WorkflowAgent` step inside the Phase 2 `LoopAgent` that validates generated code against a 6-point rubric: Syntactic Correctness, Completeness, Integration Wiring, Security, Boilerplate Relevance, and Best Practices. Sets a `validation_passed` flag in the context on success. |

---

## 3. Ingestion Plane (Managed Pipelines)

The Ingestion Plane handles the end-to-end processing of both unstructured content (SharePoint patterns) and structured infrastructure definitions (Terraform/CloudFormation) into Vertex AI Search. It also maintains a dedicated data store for service-level HA/DR documentation. It uses managed pipelines to consolidate metadata, diagrams, text, and code schemas into a unified knowledge graph.

### 3.1 Design Principles

1.  **Linear Processing**: Processes each pattern end-to-end in a single managed pipeline to ensure simplicity and reliability.
2.  **Multimodal Extraction**: Uses Gemini 1.5 Flash to "read" architectural diagrams and convert them into searchable text descriptions.
3.  **Content Enrichment**: Injects AI-generated diagram descriptions directly into the HTML content to improve RAG retrieval accuracy.
4.  **Managed Indexing**: Leverages Google Cloud Discovery Engine's "Unstructured Data with Metadata" model for simplified state management.
5.  **Media Offloading**: Stores images reliably in GCS while updating HTML references to point to the permanent storage.
6.  **Real-Time Component Resolution**: Component schema resolution is performed at inference time via real-time lookups against GitHub (MCP + PyGithub) and AWS Service Catalog — ensuring the system always works with the latest module definitions.

### 3.2 End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    participant Pipeline as Vertex Search Pipeline
    participant SP as SharePoint Client
    participant Gemini as Gemini 1.5 Flash
    participant GCS as Cloud Storage
    participant ES as Vertex Search (Discovery Engine)

    Pipeline->>SP: fetch_pattern_list()
    SP-->>Pipeline: patterns[] (Metadata)

    loop For each pattern
        Pipeline->>SP: fetch_page_html(url)
        SP-->>Pipeline: raw_html
        
        Note over Pipeline,GCS: Image Processing Phase
        Pipeline->>Pipeline: Extract <img> tags limit=2
        
        loop For each image
            Pipeline->>SP: download_image(src)
            SP-->>Pipeline: image_bytes
            
            par Parallel Analysis & Upload
                Pipeline->>Gemini: generate_content(image + prompt)
                Gemini-->>Pipeline: text_description
            and
                Pipeline->>GCS: upload_blob(image)
                GCS-->>Pipeline: public_url
            end
            
            Pipeline->>Pipeline: Update HTML <img> src & alt
        end
        
        Note over Pipeline,ES: Enrichment & Indexing
        Pipeline->>Pipeline: _enrich_html_content(html + descriptions)
        Pipeline->>Pipeline: Map metadata to struct_data
        
        Pipeline->>ES: write_document(id, content=html, struct_data)
        ES-->>Pipeline: 200 OK
    end
```

### 3.3 End-to-End Flow Description: Vertex Search Pipeline

This pipeline is responsible for unstructured data ingestion. It transforms human-readable SharePoint pages (which contain critical visual architecture diagrams) into machine-searchable text content for the RAG system.

#### Initialization & Configuration
1.  **Environment Setup**: Loads credentials for SharePoint (MSAL), Google Cloud Storage (Service Account), and Vertex AI (ADC).
2.  **Model Loading**: Initializes the `gemini-1.5-flash` model, chosen for its cost-effective multimodal capabilities and low latency.
3.  **Client Initialization**: establishes connections to:
    *   **SharePoint**: For fetching lists and page content.
    *   **GCS**: For long-term image storage.
    *   **Discovery Engine**: For updating the search index.

#### Execution Workflow (`run_ingestion`)
The pipeline operates in a batch mode, processing the entire pattern catalog sequentially.

1.  **List Retrieval**: calls `sp_client.fetch_pattern_list()` to retrieve metadata for all architecture patterns (ID, Title, Approval Status).
2.  **Sequential Processing**: Iterates through each pattern. Errors in one pattern are logged (soft failure) to allow others to proceed.

#### Pattern Processing Logic (`process_single_pattern`)
For each pattern, the pipeline performs a linear sequence of transformations:

1.  **HTML Extraction**: Fetches the raw HTML body of the SharePoint page.
2.  **Multimodal Transformation (Visual -> Text)**:
    *   **Parsing**: Uses `BeautifulSoup` to identify image tags.
    *   **Filtering**: Targets specifically the *first two images*, which canonically represent the Component Diagram and Sequence Diagram.
    *   **Download**: Retrieves the authenticated image binaries from SharePoint.
    *   **Analysis**: Sends the image bytes to **Gemini 1.5 Flash** with a prompt: *"Analyze this technical architecture diagram. Provide a detailed textual description..."*
    *   **Offloading**: Uploads the images to a public-read GCS bucket to replace ephemeral SharePoint links.
    *   **Rewriting**: Updates the HTML `<img>` tags with the new `gs://` (https based) URLs and embeds the generated description into the `alt` text.
3.  **Content Enrichment**:
    *   Creates a new HTML division: `<div class="ai-generated-context">`.
    *   Injects the full text of the Gemini-generated diagram descriptions into this div at the top of the document.
    *   **Why?**: This ensures that when Vertex Search creates embeddings for the document, the "visual" knowledge is fully represented in the vector space, allowing users to search for "systems that use load balancers" even if that text only existed in the image.
4.  **Indexing (Vertex AI Search)**:
    *   **Metadata Mapping**: Maps SharePoint list fields (Title, Owner, Maturity, Status) to the pre-defined `struct_data` schema.
    *   **Upsert**: Calls `doc_client.write_document` with the enriched HTML as `content` and the metadata dictionary. This replaces any existing version of the document.

### 3.4 Real-Time Component Resolution

The architecture uses **on-demand, real-time lookups** performed at inference time by the `ComponentSpecStep` workflow agent. This ensures the system always works with the latest module definitions.

#### Architecture Overview

```mermaid
graph LR
    subgraph "Inference Time (Real-Time)"
        Agent[ComponentSpecStep<br/>WorkflowAgent]
        Sources[component_sources.py<br/>Type Normalization]
        
        Agent --> Sources
        Sources --> GitMCP[GitHub MCP Client]
        Sources --> AWSSC[Service Catalog Client]
    end
    
    subgraph "Tier 1: GitHub"
        GitMCP -->|MCP Protocol| MCPServer[GitHub MCP Server]
        GitMCP -->|Fallback| PyGithub[PyGithub REST API]
        MCPServer --> Repos[Terraform Repos<br/>variables.tf / outputs.tf]
        PyGithub --> Repos
    end
    
    subgraph "Tier 2: AWS"
        AWSSC -->|boto3| SC[AWS Service Catalog]
        SC --> Products[CloudFormation Products<br/>Parameters & Constraints]
    end
```

#### Component Resolution Flow

1.  **Type Normalization**: Raw component types extracted by the LLM (e.g., "postgres", "k8s", "redis") are mapped to canonical forms (e.g., `rds_instance`, `eks_cluster`, `elasticache`) using a 40+ entry alias dictionary in `component_sources.py`.

2.  **Tier 1 — GitHub MCP Lookup**:
    *   The `GitHubMCPTerraformClient` searches configured GitHub organization repositories for matching Terraform modules.
    *   **Primary path**: Uses the GitHub MCP Server protocol with tools like `search_code`, `search_repositories`, and `get_file_contents`.
    *   **Fallback path**: If MCP is unavailable, falls back to PyGithub REST API, walking the repository tree to find matching `variables.tf` files.
    *   **HCL Parsing**: Uses `python-hcl2` for structural parsing with a regex fallback for edge cases.
    *   Returns `TerraformModuleSpec` dataclasses containing variables, outputs, and metadata.

3.  **Tier 2 — AWS Service Catalog Lookup** (Fallback):
    *   If no GitHub module is found, the `ServiceCatalogClient` searches AWS Service Catalog for matching products using `boto3`.
    *   Extracts the latest provisioning artifact and its parameters, constraints, and allowed values.
    *   Returns `ServiceCatalogProductSpec` dataclasses with full parameter definitions.
    *   Results are cached in-memory to reduce API calls.

4.  **Schema Assembly**: Retrieved schemas from both tiers are combined and passed to the LLM for structured component extraction, producing a JSON dependency graph with topological ordering via `graphlib.TopologicalSorter`.

#### Configuration

| Setting | Source | Default |
|---------|--------|---------|
| GitHub Repos | `GITHUB_TERRAFORM_REPOS` env var | `["rnerurkar/engen-infrastructure"]` |
| AWS Region | `AWS_DEFAULT_REGION` env var | `us-east-1` |
| AWS Profile | `AWS_PROFILE` env var | `default` |
| GitHub PAT | `GITHUB_PERSONAL_ACCESS_TOKEN` env var | Required for MCP/PyGithub |

### 3.5 Service HA/DR Ingestion Pipeline

The Service HA/DR Ingestion Pipeline processes service-level HA/DR documentation from SharePoint into a **dedicated** Vertex AI Search data store (`service-hadr-datastore`). Each service (e.g., Amazon RDS, AWS Lambda) has its own HA/DR documentation page that describes how the service behaves under different DR strategies during provisioning, failover, and failback scenarios.

> **Key Difference from Pattern Ingestion (3.3):** This pipeline does not process architecture diagrams for visual analysis. Instead, it focuses on structured metadata extraction and hierarchical chunking by DR strategy and lifecycle phase.

#### 3.5.1 Design Principles

1.  **Hierarchical Chunking**: Content is split first by DR strategy heading, then by lifecycle phase heading, then by a sliding word-count window (1500 words, 200-word overlap). This preserves contextual boundaries.
2.  **Rich Structured Metadata**: Every chunk carries `service_name`, `service_type` (Compute | Storage | Database | Network), `dr_strategy`, and `lifecycle_phase` fields. This enables precise metadata-filtered retrieval at inference time.
3.  **HA/DR Diagram Handling**: HA/DR diagrams in the source pages are downloaded, stored in GCS, and replaced in the text with LLM-generated textual descriptions (using Gemini 1.5 Flash) so the visual knowledge is captured in the vector space.
4.  **Separation of Concerns**: Uses a dedicated data store separate from the pattern document store. This prevents cross-contamination and enables independent scaling.

#### 3.5.2 End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    participant Pipeline as Service HA/DR Pipeline
    participant SP as SharePoint Client
    participant Gemini as Gemini 1.5 Flash
    participant GCS as Cloud Storage
    participant ES as Vertex AI Search<br/>(HA/DR Data Store)

    Pipeline->>SP: fetch_service_hadr_list()
    SP-->>Pipeline: service_list[] (from SP_HADR_LIST_ID)

    loop For each service
        Pipeline->>SP: fetch_page_html(service.page_url)
        SP-->>Pipeline: raw_html

        Note over Pipeline,GCS: Image Processing Phase
        loop For each <img> tag
            Pipeline->>SP: download_image(src)
            SP-->>Pipeline: image_bytes

            Pipeline->>Gemini: describe_diagram(image_bytes)
            Gemini-->>Pipeline: text_description

            Pipeline->>GCS: upload_blob(services/{name}/hadr-diagrams/)
            GCS-->>Pipeline: OK

            Pipeline->>Pipeline: Replace <img> with description text
        end

        Note over Pipeline,ES: Hierarchical Chunking Phase
        Pipeline->>Pipeline: Extract plain text from HTML
        Pipeline->>Pipeline: Split by DR Strategy heading
        Pipeline->>Pipeline: Split each strategy by Lifecycle Phase heading
        Pipeline->>Pipeline: Window-chunk each phase (1500w / 200w overlap)

        Note over Pipeline,ES: Indexing Phase
        loop For each chunk
            Pipeline->>Pipeline: Attach struct_data metadata
            Pipeline->>ES: create_document(id, content, struct_data)
            ES-->>Pipeline: 200 OK
        end
    end
```

#### 3.5.3 End-to-End Flow Description

1.  **Service Discovery**: The pipeline reads the service catalog from a **dedicated SharePoint List** (`SP_HADR_LIST_ID`) via the `SharePointClient.fetch_service_hadr_list()` method. Each list item provides the `service_name` (from the `ServiceName` column), `service_description` (`ServiceDescription`), `service_type` (`ServiceType` — Compute | Storage | Database | Network), and `page_url` (from the `HADRPageLink` hyperlink column) pointing to the service's HA/DR documentation page in SharePoint. OData pagination is handled automatically.
2.  **HTML Extraction**: For each service, the pipeline fetches the raw HTML body from the SharePoint page URL.
3.  **HA/DR Diagram Processing**: This pipeline processes **all** `<img>` tags in the document:
    *   Downloads the image from SharePoint.
    *   Sends it to **Gemini 1.5 Flash** with the prompt: *"Analyse this HA/DR architecture diagram. Describe the infrastructure components, their redundancy setup, replication flows, and failover mechanisms."*
    *   Uploads the original image to GCS under `services/{safe_name}/hadr-diagrams/diagram_{n}.png`.
    *   Replaces the HTML `<img>` tag with the generated description.
4.  **Hierarchical Chunking**: The enriched plain text is split using a three-level hierarchy:
    *   **Level 1 — DR Strategy**: Heading detection using regex patterns (`DR_STRATEGY_PATTERNS`) identifies the four DR strategies: Backup and Restore, Pilot Light On Demand, Pilot Light Cold Standby, and Warm Standby.
    *   **Level 2 — Lifecycle Phase**: Within each strategy section, heading detection using `LIFECYCLE_PHASE_PATTERNS` splits content into: Initial Provisioning, Failover, and Failback.
    *   **Level 3 — Word Window**: Each phase section is further split by a sliding word window (1500 words max, 200-word overlap) to stay within embedding model limits.

    The resulting chunk tree for a single service document looks like this:

    ```
    Full Service HA/DR Document (e.g., Amazon RDS)
    │
    ├── _split_by_dr_strategy()          ← Level 1: splits into 4 DR strategy sections
    │   │
    │   ├── "Backup and Restore" section (full text)
    │   │   │
    │   │   ├── _split_by_lifecycle_phase()   ← Level 2: splits into 3 lifecycle sub-sections
    │   │   │   │
    │   │   │   ├── "Initial Provisioning" text
    │   │   │   │   │
    │   │   │   │   ├── _size_based_chunk()   ← Level 3: splits into N chunks of ~1500 words
    │   │   │   │   │   ├── Chunk 0  ← stored as a Document in Vertex AI Search
    │   │   │   │   │   ├── Chunk 1
    │   │   │   │   │   └── Chunk 2
    │   │   │   │
    │   │   │   ├── "Failover" text
    │   │   │   │   ├── Chunk 3
    │   │   │   │   └── Chunk 4
    │   │   │   │
    │   │   │   └── "Failback" text
    │   │   │       └── Chunk 5
    │   │
    │   ├── "Pilot Light On Demand" section
    │   │   ├── "Initial Provisioning" → Chunk 6, 7
    │   │   ├── "Failover" → Chunk 8
    │   │   └── "Failback" → Chunk 9
    │   │
    │   ├── "Pilot Light Cold Standby" section
    │   │   ├── "Initial Provisioning" → Chunk 10
    │   │   ├── "Failover" → Chunk 11, 12
    │   │   └── "Failback" → Chunk 13
    │   │
    │   └── "Warm Standby" section
    │       ├── "Initial Provisioning" → Chunk 14, 15
    │       ├── "Failover" → Chunk 16
    │       └── "Failback" → Chunk 17
    ```

    Each leaf chunk is stored as a Document in the Vertex AI Search data store with a unique ID composed of `{service_name}_{chunk_index}`. The `chunk_index` provides global ordering across the entire service document, preserving the strategy → phase → position hierarchy.

5.  **Metadata Attachment**: Every chunk receives a `struct_data` dictionary containing: `service_name`, `service_description`, `service_type`, `dr_strategy`, `lifecycle_phase`, `chunk_index`, `diagram_gcs_urls`, and `diagram_descriptions`. For example, a chunk from the "Failover" phase of the "Backup and Restore" strategy for Amazon RDS would be stored as:

    ```json
    {
      "id": "Amazon_RDS_3",
      "content": "During failover, the RDS Multi-AZ instance automatically promotes the standby replica in the DR region. DNS endpoint remains the same. The promotion typically completes within 60-120 seconds. Application connection strings do not need to change because...",
      "struct_data": {
        "service_name": "Amazon RDS",
        "service_description": "Managed relational database service",
        "service_type": "Database",
        "dr_strategy": "Backup and Restore",
        "lifecycle_phase": "Failover",
        "chunk_index": 3,
        "diagram_gcs_urls": ["gs://engen-service-hadr-images/services/Amazon_RDS/hadr-diagrams/diagram_3.png"],
        "diagram_descriptions": ["A Multi-AZ RDS deployment showing the primary instance in us-east-1a with synchronous replication to the standby in us-east-1b. During failover, Route 53 health checks detect the primary failure and DNS is updated to point at the standby, which is promoted to primary within 60-120 seconds."]
      }
    }
    ```

    The `diagram_gcs_urls` and `diagram_descriptions` fields link the chunk to the original HA/DR architecture diagrams that appeared in the same section of the SharePoint page. During ingestion, each `<img>` tag is processed by Gemini Vision to produce a text description; the original image is stored on GCS. At retrieval time, these fields are returned alongside the chunk text so that downstream generators can use the diagram descriptions as **visual one-shot context** when producing new HA/DR text and diagrams.

    This structure enables the `HADRSectionsStep` workflow agent to issue targeted queries like *"retrieve all Failover chunks for Amazon RDS under the Warm Standby strategy"* using metadata-filtered hybrid search, returning only the most relevant passages — and their associated diagram references — without cross-contamination from other services or strategies.

6.  **Indexing**: Each chunk is upserted as a Document in the HA/DR data store using the Discovery Engine `CreateDocumentRequest` API.

#### 3.5.4 Data Store Schema

| Metadata Field | Type | Example | Purpose |
|----------------|------|---------|----------|
| `service_name` | String | `"Amazon RDS"` | Exact-match filter during retrieval |
| `service_description` | String | `"Managed relational DB service"` | Context enrichment |
| `service_type` | String | `"Database"` | Category filter (Compute, Storage, Database, Network) |
| `dr_strategy` | String | `"Warm Standby"` | Strategy-scoped retrieval |
| `lifecycle_phase` | String | `"Failover"` | Phase-level precision |
| `chunk_index` | Integer | `3` | Ordering within a document |
| `diagram_gcs_urls` | List[String] | `["gs://…/diagram_3.png"]` | GCS paths to original HA/DR diagrams that appeared in this chunk's source section |
| `diagram_descriptions` | List[String] | `["A Multi-AZ RDS deployment…"]` | AI-generated text descriptions of those diagrams (produced by Gemini Vision during ingestion) |

#### 3.5.5 Configuration

| Setting | Source | Default |
|---------|--------|---------|
| HA/DR Data Store ID | `SERVICE_HADR_DS_ID` env var | `service-hadr-datastore` |
| HA/DR GCS Bucket | `SERVICE_HADR_GCS_BUCKET` env var | `engen-service-hadr-images` |
| HA/DR Service List | `SP_HADR_LIST_ID` env var | SharePoint List ID (required) |

---

## 4. Serving Plane

The Serving Plane uses an ADK workflow agent system to analyze architecture diagrams, retrieve relevant "donor" patterns, generate comprehensive documentation including HA/DR sections, create Infrastructure-as-Code (IaC) artifacts, and publish the results to SharePoint and GitHub after human verification. All agent logic runs **in a single Python process** — there are no inter-agent HTTP calls.

### 4.1 Design Principles

1.  **Specialization**: Each workflow step has a single, well-defined responsibility (e.g., Retrieval, Generation, Review, Artifact Creation).
2.  **In-Process Orchestration**: All workflow steps run in the same process via ADK `SequentialAgent` + `LoopAgent` primitives, communicating through a shared `WorkflowContext` dictionary. No network serialization or HTTP overhead.
3.  **Reflection Loop**: Iterative refinement (Generate → Review → Generate) until quality threshold met (max 3 iterations), implemented as `LoopAgent` with exit keys.
4.  **Human-in-the-Loop**: User approval is collected via the React SPA wizard (chevron stepper) which calls orchestrator task endpoints directly (`approve_docs`, `approve_code`).
5.  **Artifact Generation**: Automated creation of deployable code based on authoritative interfaces ("Golden Samples") from GCS, with validation against a 6-point rubric.
6.  **Real-Time Schema Grounding**: Component specifications are grounded in live infrastructure schemas fetched at inference time from GitHub (via MCP or PyGithub) and AWS Service Catalog.
7.  **Phase-Based Orchestration**: The workflow is split into discrete phases (`phase1_generate_docs`, `phase2_generate_code`) with explicit approval gates between them.
8.  **Non-Blocking HA/DR Generation**: HA/DR section text generation executes **inside** the `LoopAgent` refinement loop (so the full-document reviewer critiques core + HA/DR together). HA/DR diagram generation executes **after** the loop completes. Both are wrapped in non-blocking try/except so that failures do not prevent the main pattern document from being returned.
9.  **Programmatic Diagrams**: HA/DR diagrams are generated **programmatically** from a structured `STATE_MATRIX` — zero Gemini calls, 12 diagrams in < 1 second. An opt-in AI mode is available for creative SVG layouts (`use_ai_diagrams=True`, `gemini-2.0-flash`); draw.io XML is always programmatic. GCS upload uses `asyncio.gather` with 60 s per-upload timeout.
10. **Observability**: Centralized logging, metrics tracking, and health checks (liveness/readiness) via the `ADKAgent` framework.

### 4.2 Workflow Architecture

The system runs as a single `OrchestratorAgent` process containing two ADK workflow pipelines:

**Phase 1 — Document Generation** (`Phase1DocGenerationWorkflow`):
-   `SequentialAgent` → VisionAnalysisStep → DonorRetrievalStep → `LoopAgent` (PatternGenerateStep → HADRSectionsStep → FullDocReviewStep, max 3, exit on "approved") → HADRDiagramStep

**Phase 2 — Artifact Generation** (`Phase2ArtifactWorkflow`):
-   `SequentialAgent` → ComponentSpecStep → `LoopAgent` (ArtifactGenerateStep → ArtifactValidateStep, max 3, exit on "validation_passed")

Core logic modules (PatternGenerator, VertexRetriever, PatternReviewer, ComponentSpecification, PatternArtifactGenerator, ArtifactValidator, ServiceHADRRetriever, HADRDocumentationGenerator, HADRDiagramGenerator, HADRDiagramStorage) are instantiated once at startup and shared through the `WorkflowContext` — no network calls, no serialisation overhead.

### 4.3 High-Level Sequence Diagram

```mermaid
sequenceDiagram
    participant Client as React SPA
    participant Orch as Orchestrator Agent
    participant WCtx as WorkflowContext
    participant DB as AlloyDB
    participant Async as Async Workers
    participant GitMCP as GitHub MCP Client
    participant SvcCat as Service Catalog Client

    Client->>Orch: POST /invoke {task: "phase1_generate_docs", image, title, user_id}
    
    Note over Orch,WCtx: Phase 1: Doc Generation (SequentialAgent, all in-process)
    Orch->>WCtx: Seed context (image, title, module refs)
    Orch->>Orch: VisionAnalysisStep → Gemini Vision → description
    Orch->>Orch: DonorRetrievalStep → Vertex AI Search → donor_context

    loop ContentRefinementLoop (LoopAgent, max 3)
        Orch->>Orch: PatternGenerateStep → Gemini Pro → draft_sections
        Orch->>Orch: HADRSectionsStep → parallel retrieve + generate → HA/DR sections
        Orch->>Orch: FullDocReviewStep → review full doc → approved / critique
    end

    Orch->>Orch: HADRDiagramStep → programmatic SVG + draw.io (12 diagrams, < 1s)
    Orch->>Orch: Upload to GCS, embed URLs in HA/DR sections

    Note over Orch,Client: Phase 1 Complete → User Approval
    Orch-->>Client: Return sections + full_doc + workflow_id
    Client->>Client: Store workflow_id in localStorage
    Client->>Orch: POST /invoke {task: "approve_docs", workflow_id}
    
    par Async Publishing (Docs)
        Orch->>Async: publish_docs_async(review_id)
        Async->>DB: Update Status (IN_PROGRESS → COMPLETED)
    and Continue Workflow
        Client->>Orch: POST /invoke {task: "phase2_generate_code", workflow_id}
    end

    Note over Orch,WCtx: Phase 2: Artifact Generation (SequentialAgent, all in-process)
    Orch->>WCtx: Seed context (full_doc, module refs)
    Orch->>Orch: ComponentSpecStep → real-time lookups
    Orch->>GitMCP: search_terraform_module(type)
    GitMCP-->>Orch: TerraformModuleSpec
    Orch->>SvcCat: search_product(type) [fallback]
    SvcCat-->>Orch: ServiceCatalogProductSpec

    loop ArtifactRefinementLoop (LoopAgent, max 3)
        Orch->>Orch: ArtifactGenerateStep → Golden Samples + Gemini → artifacts
        Orch->>Orch: ArtifactValidateStep → 6-point rubric → PASS / NEEDS_REVISION
    end

    Note over Orch,Client: Phase 2 Complete → User Approval
    Orch-->>Client: Return artifact bundle
    Client->>Orch: POST /invoke {task: "approve_code", workflow_id}

    par Async Publishing (Code)
        Orch->>Async: publish_code_async(review_id)
        Async->>DB: Update Status (IN_PROGRESS → COMPLETED)
    and Return Immediate Response
        Orch-->>Client: {status: "processing", pattern_id, artifact_id}
    end

    Note over Client,DB: Client Polling via Orchestrator
    loop Poll Until Complete (every 3s)
        Client->>Orch: POST /invoke {task: "get_publish_status", workflow_id}
        Orch->>DB: Check Status
        DB-->>Orch: {doc_url, code_url}
        Orch-->>Client: Status update
    end
```

### 4.4 End-to-End Flow Description

#### Phase 1: Contextualization
1.  **Analysis**: The `VisionAnalysisStep` uses Gemini Vision (via `PatternGenerator.generate_search_description`) to extract a detailed technical description from the input diagram.
2.  **Retrieval**: The `DonorRetrievalStep` uses this description to perform a hybrid search (Vector + Keyword) in Vertex AI Search (via `VertexRetriever.get_best_donor_pattern`) to find the best matching "Donor Pattern" to serve as a structural template.

#### Phase 2: Content Generation Loop (LoopAgent, In-Process)
3.  **Drafting**: The `PatternGenerateStep` invokes `PatternGenerator` with the diagram description and the donor pattern context. Gemini 1.5 Pro generates a first draft of the documentation (Problem, Solution, Architecture).
4.  **HA/DR Section Generation (Inside Loop)**: The `HADRSectionsStep` executes within the same `LoopAgent` iteration:
    *   Extracts canonical service names from the generated documentation using regex matching against the `component_sources.py` alias dictionary (40+ mappings) and a curated list of common service names. Results are cached in `WorkflowContext`.
    *   Calls `ServiceHADRRetriever.aretrieve_all_services_hadr()` in-process to query the `service-hadr-datastore` via **hybrid retrieval** (metadata filter + vector search). All N × 4 queries are dispatched in parallel via `asyncio.gather`.
    *   Calls `HADRDocumentationGenerator.extract_donor_hadr_sections()` in-process to parse the donor pattern's HTML and extract HA/DR sub-sections.
    *   Retrieval and donor extraction run in parallel via `asyncio.gather`.
    *   Calls `HADRDocumentationGenerator.agenerate_hadr_sections()` in-process — all four DR strategy sections generated in parallel via `asyncio.gather`, each with a 120 s timeout.
    *   Results include per-phase summary tables showing each service's state (Active, Standby, Scaled-Down, Not-Deployed).
5.  **Full-Document Review**: The `FullDocReviewStep` sends the complete document (core sections + HA/DR) to the `PatternReviewer`. This enables the reviewer to critique HA/DR quality alongside core content.
6.  **Refinement**: If the score is below threshold, the `LoopAgent` feeds the critique back for a revised draft. HA/DR is regenerated only if the reviewer flagged it. This repeats for up to 3 iterations.
7.  **Non-Blocking Merge**: The generated HA/DR sections are merged into the `generated_sections` dictionary under the `HA/DR` key. If HA/DR generation fails for any reason, a placeholder message is inserted and the workflow continues normally — the main pattern document is never blocked by HA/DR failures.

#### Phase 2b: HA/DR Diagram Generation & Storage (Programmatic, Non-Blocking)
8.  **Programmatic Diagram Generation**: The `HADRDiagramStep` runs **after** the `LoopAgent` completes. `HADRDiagramGenerator` produces all 12 diagrams (4 DR strategies × 3 lifecycle phases) **programmatically** from a structured `STATE_MATRIX` — a dictionary mapping each `(strategy, phase)` to a `RegionStates` dataclass specifying the exact state (Active, Standby, Scaled-Down, Not-Deployed) for core vs. non-core services in primary and DR regions. The `_is_data_service()` classifier distinguishes data services (databases, storage) from compute services. SVG is built by `_build_programmatic_svg()` and draw.io XML by `_build_programmatic_drawio()` (using the `DRAWIO_SERVICE_ICONS` registry). **Zero Gemini calls, < 1 second for all 12 diagrams, zero tokens consumed.**
9.  **Opt-In AI Mode**: When `use_ai_diagrams=True`, SVG generation uses Gemini (`gemini-2.0-flash` by default, configurable via `ai_model_name`) with `max_output_tokens=4096`. Draw.io XML remains always programmatic even in AI mode. AI mode uses `asyncio.gather` with `Semaphore(6)` concurrency control and per-diagram timeout.
10. **SVG→PNG Conversion**: PNG fallback images are generated locally from the SVG content using `svglib` + `reportlab` (with `pycairo` shim on Windows). On Linux, `cairosvg` is the primary converter.
11. **Diagram Storage**: `HADRDiagramStorage.aupload_diagram_bundle()` uploads all three artefacts per diagram to GCS in parallel with a 60 s timeout per upload.
12. **URL Embedding**: The returned diagram URLs are embedded into the HA/DR markdown sections so that the rendered documentation contains inline SVG references and links to the editable draw.io files.

#### Phase 3: Governance (Point 1) & Async Doc Publishing
13. **Pattern Verification**: The Orchestrator returns the generated documentation — including HA/DR sections with embedded diagram URLs — to the React SPA. The user reviews the pattern sections and the HA/DR content (with inline diagrams) in collapsible expander panels, then clicks "Approve & Continue" in the chevron wizard.
14. **Approval**: The React SPA calls the `approve_docs` task (passing the `workflow_id`). The Orchestrator updates AlloyDB review status, persists the workflow state to `CODE_GEN` via `WorkflowStateManager`, and receives a `review_id`.
15. **Async Publishing**: It immediately spawns a background task to publish the documentation to SharePoint, using the `review_id` to track progress in AlloyDB. The workflow *does not wait* for this to finish but proceeds to artifact generation.

#### Phase 4: Pattern Synthesis (In-Process ADK Workflow)
16. **Context Seeding**: The Orchestrator builds a new `WorkflowContext` containing the full document text, and references to the `ComponentSpecification`, `PatternArtifactGenerator`, and `ArtifactValidator` core logic modules.
17. **Real-Time Schema Resolution**: The `ComponentSpecStep` extracts component keywords from the documentation, normalizes them using the `component_sources.py` alias dictionary (40+ mappings), and performs a two-tier real-time lookup:
    *   **Tier 1 (GitHub)**: Searches configured GitHub repositories via the MCP Server protocol (with PyGithub fallback) for matching Terraform modules, parsing `variables.tf` and `outputs.tf` files using `python-hcl2`.
    *   **Tier 2 (AWS)**: Falls back to AWS Service Catalog via `boto3` to find matching CloudFormation products with their provisioning parameters and constraints.
18. **Comprehensive Specification**: It generates a structured dependency graph grounded in these real-world schemas, with topological ordering via `graphlib.TopologicalSorter` to determine execution order. The specification is stored in the `WorkflowContext`.
19. **Artifact Generation Loop**: The `ArtifactRefinementLoop` (`LoopAgent`, max 3 iterations) runs:
    *   **ArtifactGenerateStep**: Retrieves enterprise-approved "Golden Sample" IaC templates from GCS, then generates both **Infrastructure as Code (Terraform)** and **Reference Implementation (Boilerplate)** in a single context window using Gemini.
    *   **ArtifactValidateStep**: Checks the generated code against a 6-point rubric: Syntactic Correctness (Critical), Completeness (Critical), Integration Wiring (Critical), Security (High), Boilerplate Functional Relevance (Medium), Best Practices (Medium). Sets `validation_passed` in the context on success, or stores the critique for the next iteration.
20. **Loop Exit**: The `LoopAgent` exits when `validation_passed` is set in the `WorkflowContext`, or after 3 iterations.

#### Phase 5: Governance (Point 2) & Async Code Publishing
21. **Artifact Verification**: The validated code bundle is sent back to the React SPA for the user to review and approve.
22. **Async Publishing**: On approval, the Orchestrator spawns a background task to push the code to GitHub via the REST API (direct push to the configured branch). The workflow state is persisted to `PUBLISH` via `WorkflowStateManager`.
23. **Immediate Return**: The Orchestrator returns a `processing` status to the client, along with the review IDs needed to track the background tasks.

#### Phase 6: Client Polling
24. **Status Check**: The React SPA's `PublishStep` component polls the orchestrator's `get_publish_status` task every 3 seconds using the returned IDs and `workflow_id`.
25. **Completion**: Once the background tasks update the DB status to `COMPLETED`, the orchestrator marks the workflow state as `COMPLETED`, deactivates the `workflow_state` row, and relays the final URLs for the SharePoint page and GitHub commit back to the client. The SPA clears `localStorage("engen_workflow_id")`.


### 4.5 Response Assembly

Upon initiating the pattern generation and async publishing tasks, the Orchestrator constructs an immediate response to the client. This response facilitates non-blocking UI updates.

**Response Payload:**
-   `status`: `"workflow_completed_processing_async"`
-   `pattern_review_id`: UUID for tracking the documentation publishing status.
-   `artifact_review_id`: UUID for tracking the code publishing status.
-   `message`: Informational message about background processing.

The final URLs (SharePoint page, GitHub commit) are **not** returned here but must be retrieved via polling the AlloyDB `reviews` table.

### 4.6 Error Handling Strategy

The Orchestrator implements robust error handling for both synchronous workflow steps and asynchronous background tasks:

-   **In-Process Step Failures**: All workflow steps run in the same process, so exceptions propagate immediately. The Orchestrator catches exceptions from each phase and returns a structured error response.
-   **Validation Loop**: If artifact validation fails 3 times, the workflow halts and returns the validation errors for manual intervention.
-   **Async Publishing Fails**: 
    -   If SharePoint or GitHub API calls fail, the background worker catches the exception.
    -   It updates the AlloyDB status to `FAILED`.
    -   The client polling mechanism sees the failure and can display an error message or retry button to the user.
-   **HA/DR Generation Fails**: The entire HA/DR generation step (service name extraction, retrieval, generation) is wrapped in a top-level try/except. If any sub-step fails, a placeholder message ("*HA/DR section generation failed. Please complete manually.*") is inserted into the `generated_sections` dictionary and the workflow continues. The pattern document is never blocked by HA/DR failures.

### 4.7 Multi-Channel Publishing

The system separates the publishing of documentation and implementation code into distinct, asynchronous workflows. This ensures that documentation is available immediately upon approval, while code generation (which takes longer) proceeds in parallel.

#### 4.7.1 SharePoint (Documentation Knowledge Base)
Upon approval of the design pattern text, the `SharePointPublisher` converts the markdown content into a modern SharePoint page. This serves as the authoritative interface documentation.

#### 4.7.2 GitHub (Implementation Repository)
Upon approval of the generated artifacts, the `GitHubMCPPublisher` commits the files to the target repository using the GitHub REST API (Git tree manipulation: get ref → create tree → create commit → update ref).
*   `infrastructure/{iac_type}/`: Contains Terraform or CloudFormation templates.
*   `src/{component}/`: Contains application boilerplate code.
*   The publisher pushes directly to the configured branch (default `main`).

#### 4.7.3 SharePoint Publishing Detail

The SharePoint publishing process involves a complex conversion from Markdown to SharePoint's JSON-based Page Canvas model. It uses MS Graph API (v1.0 and beta) to create pages, add web parts, and publish them.

**Key Steps:**
1.  **Authentication**: Uses MSAL with Client Credentials flow to get a Graph API token.
2.  **Page Creation**: Creates a draft page in the `SitePages` library.
3.  **Mermaid Diagram Rendering**: `process_markdown_diagrams()` finds ` ```mermaid ` code blocks, renders them to PNG via the Kroki service, uploads the PNG to the SharePoint Site Assets library (`GeneratedDiagrams/` folder), and rewrites the markdown to reference the SharePoint-hosted image URL.
4.  **GCS Image Re-hosting**: `process_gcs_images()` finds markdown image references (`![alt](https://storage.googleapis.com/…/*.png)`) pointing to GCS-hosted HA/DR diagram PNGs, downloads each PNG, uploads it to the SharePoint Site Assets library (`GeneratedDiagrams/` folder), and rewrites the markdown URL to the SharePoint-hosted copy. SVG view links and draw.io download links remain as GCS hyperlinks — only `![](url)` image syntax is targeted.
5.  **Conversion**: Parses markdown into HTML (using `python-markdown`), sanitizes it (using `bleach` with `img` in `allowed_tags`), and wraps it in SharePoint text web parts.
6.  **Canvas Layout**: Constructs the JSON layout structure (`horizontalSections`, `columns`, `webparts`).
7.  **Publishing**: PATCHes the page content and POSTs to the `/publish` endpoint.
8.  **Status Update**: Updates AlloyDB with the final page URL.

### 4.8 Artifact Generation Workflow (Pattern Synthesis)

This workflow implements a "Pattern Synthesis" approach. Instead of generating infrastructure components in isolation, the system treats the entire architectural pattern as a single unit of generation. This ensures that cross-component dependencies (e.g., a Cloud Run service needing the name of a Cloud SQL instance) are resolved correctly during the generation phase. The entire workflow runs **in-process** as the Phase 2 ADK `SequentialAgent` + `LoopAgent`.

#### 4.8.1 System Components

| Component | Responsibility |
|-----------|----------------|
| **OrchestratorAgent** | The central state machine that drives the workflow. Builds a `WorkflowContext` with the full document and references to core logic modules, then delegates to the `Phase2ArtifactWorkflow` (`SequentialAgent`). Manages the lifecycle of the request, persists workflow state to AlloyDB via `WorkflowStateManager` at every phase transition for resumable sessions. |
| **AlloyDBManager** | **State Store**. Acts as the single source of truth for the status of both human reviews and async publishing tasks. Allows the frontend to poll for completion without blocking. |
| **ComponentSpecification** | **Analyzer**. Invoked in-process by `ComponentSpecStep`. Parses the high-level design documentation and performs **real-time lookups** against GitHub repositories (via `GitHubMCPTerraformClient`) and AWS Service Catalog (via `ServiceCatalogClient`) to extract a structured dependency graph grounded in actual infrastructure schemas. Uses `component_sources.py` for type normalization. |
| **GitHubMCPTerraformClient** | **Tier 1 Schema Source**. Searches configured GitHub repos for Terraform modules using the MCP Server protocol (with PyGithub REST API fallback). Parses `variables.tf` and `outputs.tf` using `python-hcl2`. Returns `TerraformModuleSpec` dataclasses. |
| **ServiceCatalogClient** | **Tier 2 Schema Source** (Fallback). Queries AWS Service Catalog via `boto3` for CloudFormation products, extracts provisioning parameters and constraints. Returns `ServiceCatalogProductSpec` dataclasses. Caches results in-memory. |
| **PatternArtifactGenerator** | **Synthesizer**. Invoked in-process by `ArtifactGenerateStep`. Fetches **"Golden Sample" IaC templates** from a GCS bucket to benchmark the generated code against organizational best practices. Generates a holistic "Artifact Bundle" (IaC + Boilerplate) in a single consistent pass. |
| **ArtifactValidator** | **Quality Gate**. Invoked in-process by `ArtifactValidateStep`. Inspects the generated Artifact Bundle against a 6-point rubric: Syntactic Correctness (Critical), Completeness (Critical), Integration Wiring (Critical), Security (High), Boilerplate Functional Relevance (Medium), Best Practices Adherence (Medium). Scores 0-100 with PASS/NEEDS_REVISION verdicts. |
| **GitHubMCPPublisher** | **Code Publisher**. Pushes the generated code to GitHub as a background task using direct REST API Git tree manipulation. |
| **SharePointPublisher** | **Docs Publisher**. Publishes design documentation to the enterprise SharePoint knowledge base as a background task. Converts Markdown to SharePoint modern page canvas layout with web parts, renders Mermaid diagrams via Kroki, and re-hosts GCS-stored HA/DR PNG diagrams to SharePoint Site Assets for inline rendering. |

#### 4.8.2 Component Diagram

The following diagram illustrates the structural relationships and information flow between the synthesis components, highlighting the in-process execution model.

```mermaid
graph TD
    subgraph "Client Layer"
        UI[React SPA]
    end

    subgraph "Orchestration Layer"
        Orch[Orchestrator Agent]
        DB[(AlloyDB<br/>State Store)]
        WFS[(AlloyDB<br/>Workflow State)]
    end

    subgraph "Phase 2 ADK Workflow (in-process)"
        CompSpec["ComponentSpecStep<br/>(WorkflowAgent)"]
        ArtGen["ArtifactGenerateStep<br/>(WorkflowAgent)"]
        ArtVal["ArtifactValidateStep<br/>(WorkflowAgent)"]
    end

    subgraph "Core Logic Modules"
        CompSpecEngine["ComponentSpecification"]
        ArtGenEngine["PatternArtifactGenerator"]
        ArtValEngine["ArtifactValidator"]
    end

    subgraph "Real-Time Component Sources"
        CompSources["component_sources.py<br/>Type Normalization"]
        GitMCP["GitHub MCP Client<br/>(MCP + PyGithub fallback)"]
        SvcCat["Service Catalog Client<br/>(boto3)"]
    end

    subgraph "Async Workers"
        PubDocs[SharePoint<br/>Publisher]
        PubCode[GitHub<br/>Publisher]
    end

    subgraph "External Resources"
        GCS[GCS Bucket<br/>Golden Samples]
        GitRepos[GitHub Terraform<br/>Repositories]
        AWSSC[AWS Service<br/>Catalog]
    end

    %% Data Flow
    UI -->|Start| Orch
    UI -.->|Poll Status via Orch| DB
    UI -.->|Resume via Orch| WFS

    Orch -->|Update State| DB
    Orch -->|Save Phase| WFS
    Orch -->|Trigger Async| PubDocs
    Orch -->|Trigger Async| PubCode

    PubDocs -->|Update State| DB
    PubCode -->|Update State| DB
    
    GCS -->|Fetch Templates| ArtGenEngine
    GCS -->|Fetch Templates| ArtValEngine

    Orch -->|WorkflowContext| CompSpec
    CompSpec -->|in-process| CompSpecEngine
    CompSpecEngine -->|Normalize Types| CompSources
    CompSources -->|Tier 1 Lookup| GitMCP
    CompSources -->|Tier 2 Fallback| SvcCat
    GitMCP -->|Search & Parse| GitRepos
    SvcCat -->|Query Products| AWSSC

    CompSpec -->|Specification in context| ArtGen
    ArtGen -->|in-process| ArtGenEngine
    ArtGen -->|Artifacts in context| ArtVal
    ArtVal -->|in-process| ArtValEngine
```

#### 4.8.3 Sequence Diagram

This sequence diagram details the lifecycle of a request from approved documentation to published artifacts, emphasizing the in-process execution model.

```mermaid
sequenceDiagram
    autonumber
    participant Client as React SPA
    participant Orch as Orchestrator Agent
    participant WCtx as WorkflowContext
    participant CompStep as ComponentSpecStep
    participant GitMCP as GitHub MCP Client
    participant SvcCat as Service Catalog Client
    participant GenStep as ArtifactGenerateStep
    participant GCS as GCS Bucket
    participant ValStep as ArtifactValidateStep
    participant DB as AlloyDB
    participant Async as Background Tasks

    Note over Orch, Async: Phase 3: Pattern Approval & Async Doc Publishing
    
    Client->>Orch: POST /invoke {task: "approve_docs", workflow_id}
    Orch->>DB: Create review record (PID-1)
    
    par Fire & Forget
        Orch->>Async: publish_docs(PID-1)
        Async->>DB: UPDATE status='IN_PROGRESS'
        Note right of Async: Uploads to SharePoint...
        Async->>DB: UPDATE status='COMPLETED' url='...'
    and Continue Execution
        Client->>Orch: POST /invoke {task: "phase2_generate_code", workflow_id}
    end
    
    Note over Orch, ValStep: Phase 4: In-Process Artifact Generation (ADK Workflow)

    Orch->>WCtx: Seed context (full_doc, module refs)
    
    Orch->>CompStep: Run ComponentSpecStep (in-process)
    CompStep->>CompStep: Extract keywords via LLM
    CompStep->>CompStep: Normalize types (component_sources.py)
    
    loop For each component type
        CompStep->>GitMCP: search_terraform_module(type)
        alt Module found in GitHub
            GitMCP-->>CompStep: TerraformModuleSpec (variables, outputs)
        else Not found — Fallback
            GitMCP-->>CompStep: None
            CompStep->>SvcCat: search_product(type)
            SvcCat-->>CompStep: ServiceCatalogProductSpec (parameters)
        end
    end
    
    CompStep->>CompStep: Topological sort (graphlib)
    CompStep->>WCtx: Store ComponentSpecification

    Note over Orch, ValStep: ArtifactRefinementLoop (LoopAgent, max 3)
    
    loop Quality Assurance Loop (exit on validation_passed)
        Orch->>GenStep: Run ArtifactGenerateStep (in-process)
        GenStep->>GCS: fetch_golden_samples(types)
        GCS-->>GenStep: approved_templates
        GenStep->>WCtx: Store ArtifactBundle
        
        Orch->>ValStep: Run ArtifactValidateStep (in-process)
        ValStep->>WCtx: Read ArtifactBundle
        ValStep->>ValStep: 6-point rubric validation
        ValStep->>WCtx: Store ValidationResult + set validation_passed (or critique)
    end

    Note over Orch, Async: Phase 5: Artifact Approval & Async Code Publishing

    Orch-->>Client: Return artifact bundle
    Client->>Orch: POST /invoke {task: "approve_code", workflow_id}

    par Fire & Forget
        Orch->>Async: publish_code(AID-2)
        Async->>DB: UPDATE status='IN_PROGRESS'
        Note right of Async: Pushes to GitHub (REST API)...
        Async->>DB: UPDATE status='COMPLETED' url='...'
    and Return Immediate Result
        Orch-->>Client: {status: "processing", p_id: "PID-1", a_id: "AID-2"}
    end

    Note over Client, DB: Phase 6: Client-Side Polling
    
    loop Poll until both COMPLETED
        Client->>Orch: POST /invoke {task: "get_publish_status", workflow_id}
        Orch->>DB: SELECT status, url FROM reviews
        DB-->>Orch: {doc_status, code_status}
        Orch-->>Client: Status update
    end
```

**Step-by-Step Explanation:**

1.  **Approve Documentation**: The user approves the generated documentation via the React SPA wizard.
2.  **Trigger Async Publish (Docs)**: The Orchestrator immediately spawns a background task (`asyncio.create_task`) to publish the docs.
3.  **Build Phase 2 Context**: The Orchestrator builds a `WorkflowContext` seeded with the full document text and references to `ComponentSpecification`, `PatternArtifactGenerator`, and `ArtifactValidator` core logic modules.
4.  **ComponentSpecStep (In-Process)**: The `Phase2ArtifactWorkflow` `SequentialAgent` runs the `ComponentSpecStep` first.
5.  **Keyword Extraction**: The step uses Gemini 1.5 Pro to extract infrastructure component keywords from the documentation.
6.  **Type Normalization**: Raw keywords are normalized to canonical component types using the `component_sources.py` alias dictionary (40+ mappings, e.g., "postgres" → `rds_instance`).
7.  **Real-Time Schema Lookup (Tier 1 — GitHub)**: For each component type, the `GitHubMCPTerraformClient` searches configured repositories for matching Terraform modules. Found modules are parsed from `variables.tf` and `outputs.tf` using `python-hcl2`.
8.  **Real-Time Schema Lookup (Tier 2 — AWS)**: If no GitHub module is found for a component, the `ServiceCatalogClient` queries AWS Service Catalog via `boto3` for matching CloudFormation products.
9.  **Return Specification**: The step assembles all retrieved schemas and uses the LLM to produce a structured JSON dependency graph, topologically sorted via `graphlib.TopologicalSorter`. The result is stored in the `WorkflowContext`.
10. **ArtifactRefinementLoop**: The `LoopAgent` begins iterating.
11. **ArtifactGenerateStep (In-Process)**: Reads the specification from the context, fetches Golden Sample templates from GCS, and generates a complete bundle containing Terraform and application code.
12. **ArtifactValidateStep (In-Process)**: Validates the bundle against the 6-point rubric. On success, sets `validation_passed` in the context. On failure, stores the critique for the next iteration.
13. **Loop Exit**: The `LoopAgent` exits when `validation_passed` is set or after 3 iterations.
14. **Return Artifacts**: The Orchestrator extracts the artifacts from the `WorkflowContext` and returns them to the client.
15. **Approve Artifacts**: The user approves the code via the React SPA wizard.
16. **Trigger Async Publish (Code)**: The Orchestrator spawns a background task to push the code to GitHub via REST API.
17. **Poll Status**: The React SPA polls `get_publish_status` until both docs and code publishing are complete.

### 4.9 HA/DR Documentation & Diagram Generation Workflow

This workflow generates the High Availability / Disaster Recovery (HA/DR) section of a pattern document by synthesizing service-level HA/DR reference documentation with donor pattern examples, and produces visual component diagrams (SVG + draw.io XML + PNG) for every DR strategy × lifecycle phase combination. HA/DR section generation executes **inside** the `LoopAgent` refinement loop (as `HADRSectionsStep`), while diagram generation executes **after** the loop (as `HADRDiagramStep`). All core logic is invoked **in-process** via shared `WorkflowContext`. Diagrams are generated **programmatically** from a structured `STATE_MATRIX`, with an opt-in AI mode available.

#### 4.9.1 System Components

| Component | Responsibility |
|-----------|----------------|
| **OrchestratorAgent** | Instantiates all HA/DR core logic modules (`ServiceHADRRetriever`, `HADRDocumentationGenerator`, `HADRDiagramGenerator`, `HADRDiagramStorage`) directly and shares them across workflow steps via `WorkflowContext`. Coordinates the HA/DR generation flow through in-process `WorkflowAgent` steps. |
| **HADRSectionsStep** (in-process) | ADK `WorkflowAgent` step running **inside** the `LoopAgent`. Extracts service names (cached in `WorkflowContext`), calls `ServiceHADRRetriever` for hybrid retrieval (metadata filter + vector search, N×4 parallel queries), calls `HADRDocumentationGenerator` for donor parsing and per-strategy text generation (4 parallel, 120 s timeout), and merges results into `generated_sections["HA/DR"]`. |
| **HADRDiagramStep** (in-process) | ADK `WorkflowAgent` step running **after** the `LoopAgent`. Calls `HADRDiagramGenerator` to produce 12 diagrams programmatically (default) or via AI, then calls `HADRDiagramStorage` to upload to GCS. Embeds diagram URLs into HA/DR sections. |
| **ServiceHADRRetriever** (core logic) | Queries the `service-hadr-datastore` in Vertex AI Search using hybrid retrieval (metadata filter + vector search). Returns chunks organized as `service_name → dr_strategy → [chunks]`. Methods: `aretrieve_service_hadr` (single), `aretrieve_all_services_hadr` (bulk — dispatches all N × 4 queries in parallel via `asyncio.gather`). |
| **HADRDocumentationGenerator** (core logic) | Takes service-level HA/DR chunks, donor pattern HA/DR sections (one-shot), and pattern context. Generates one DR strategy section at a time via Gemini 1.5 Pro. Produces Markdown with per-phase summary tables. Methods: `agenerate_hadr_sections` (all 4 strategies in parallel via `asyncio.gather` with 120 s per-strategy timeout), `extract_donor_hadr_sections` (parses donor HTML using regex heading detection). |
| **HADRDiagramGenerator** (core logic) | Produces SVG, draw.io XML (with official AWS/GCP icon shapes from `DRAWIO_SERVICE_ICONS`), and PNG fallback images for every DR strategy × lifecycle phase combination (4 × 3 = 12 diagrams). **Default mode (programmatic)**: Uses `STATE_MATRIX` to build deterministic SVG via `_build_programmatic_svg()` and draw.io XML via `_build_programmatic_drawio()`. Zero Gemini calls. **Opt-in AI mode** (`use_ai_diagrams=True`): SVG generated via Gemini; draw.io XML is always programmatic. |
| **HADRDiagramStorage** (core logic) | Uploads SVG + draw.io XML + PNG to GCS in parallel via `asyncio.gather`, 60 s timeout per upload. Returns URL map `{(strategy, phase) → {svg_url, drawio_url, png_url}}`. |
| **Vertex AI Search (HA/DR Data Store)** | Dedicated data store containing service-level HA/DR documentation chunks with structured metadata for precise filtered retrieval. Populated by the Service HA/DR Ingestion Pipeline (Section 3.5). |
| **GCS (Diagram Bucket)** | Stores diagram artefacts at path `patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.{svg,drawio,png}`. During SharePoint publishing, PNG files are **re-hosted to SharePoint Site Assets** for inline rendering; SVG and draw.io files remain served from GCS as view/download links. |

#### 4.9.2 Component Diagram

```mermaid
graph TD
    subgraph "Phase 1 SequentialAgent (in-process)"
        subgraph "LoopAgent (max 3 iterations)"
            Draft[PatternGenerateStep<br/>PatternGenerator]
            HADR_Step[HADRSectionsStep<br/>- Extract service names<br/>- Retrieve + Generate text]
            Review[FullDocReviewStep<br/>PatternReviewer]
        end
        DiagStep[HADRDiagramStep<br/>- Programmatic SVG + draw.io<br/>from STATE_MATRIX]
    end

    subgraph "Core Logic (shared via WorkflowContext)"
        Retriever[ServiceHADRRetriever]
        Generator[HADRDocumentationGenerator]
        DiagGen[HADRDiagramGenerator<br/>- STATE_MATRIX<br/>- _build_programmatic_svg<br/>- _build_programmatic_drawio<br/>- DRAWIO_SERVICE_ICONS]
        DiagStore[HADRDiagramStorage]
        PNGConv[SVG→PNG<br/>svglib + reportlab]
    end

    subgraph "External Services"
        HADRDS[(Vertex AI Search<br/>service-hadr-datastore)]
        GeminiText[Gemini 1.5 Pro<br/>Text Generation]
        DiagGCS[(GCS Bucket<br/>hadr-diagrams)]
    end

    subgraph "Donor Context"
        DonorHTML[Donor Pattern HTML]
    end

    %% Text Generation Flow (in-process)
    Draft -->|doc_text| HADR_Step
    HADR_Step -->|in-process| Retriever
    Retriever -->|metadata filter + vector| HADRDS
    HADRDS -->|service→strategy→chunks| Retriever

    DonorHTML -->|in-process| Generator
    Generator -->|donor_hadr_sections| HADR_Step

    HADR_Step -->|in-process| Generator
    Generator -->|prompt per strategy| GeminiText
    GeminiText -->|markdown section| Generator

    HADR_Step -->|merged doc| Review
    Review -->|critique/approve| Draft

    %% Diagram Generation Flow (in-process, programmatic by default)
    DiagStep -->|in-process| DiagGen
    DiagGen -->|programmatic SVG + draw.io| DiagGen
    DiagGen -->|SVG bytes| PNGConv
    PNGConv -->|PNG bytes| DiagGen
    DiagStep -->|in-process| DiagStore
    DiagStore -->|upload SVG+XML+PNG| DiagGCS
    DiagGCS -->|public URLs| DiagStore
```

#### 4.9.3 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Orch as OrchestratorAgent
    participant WCtx as WorkflowContext
    participant Ret as ServiceHADRRetriever<br/>(core logic, in-process)
    participant HADRDS as Vertex AI Search<br/>(HA/DR Data Store)
    participant Gen as HADRDocumentationGenerator<br/>(core logic, in-process)
    participant Gemini as Gemini 1.5 Pro
    participant DiagGen as HADRDiagramGenerator<br/>(core logic, in-process)
    participant DiagStore as HADRDiagramStorage<br/>(core logic, in-process)
    participant GCS as GCS (Diagram Bucket)

    Note over Orch,GCS: Inside LoopAgent — HADRSectionsStep (in-process)
    
    Orch->>WCtx: Check cached service_names
    alt First iteration (not cached)
        Orch->>Orch: _extract_service_names_from_doc(doc_text)
        Orch->>WCtx: Cache service_names
    end
    WCtx-->>Orch: service_names[] (e.g. ["Amazon RDS", "AWS Lambda"])

    par Parallel: Retrieval + Donor Extraction (asyncio.gather)
        Orch->>Ret: aretrieve_all_services_hadr(service_names)
        par Async Parallel (N×4 queries via asyncio.gather)
            Ret->>HADRDS: SearchRequest(filter=svc1+strategy1, query=semantic)
            Ret->>HADRDS: SearchRequest(filter=svc1+strategy2, query=semantic)
            Note right of Ret: ...all N×4 queries dispatched in parallel
            HADRDS-->>Ret: SearchResponse (extractive answers + metadata)
        end
        Ret-->>Orch: service_hadr_docs {svc→strategy→[chunks]}
    and
        Orch->>Gen: extract_donor_hadr_sections(donor_html)
        Gen-->>Orch: donor_hadr_sections {strategy→text}
    end

    Orch->>Orch: Build pattern_context (title, solution, services)

    par Async Parallel (4 strategies via asyncio.gather, 120s timeout each)
        Orch->>Gen: agenerate_hadr_sections(strategy1)
        Gen->>Gemini: generate_content(prompt, temp=0.3)
        Gemini-->>Gen: markdown section with summary tables
    and
        Orch->>Gen: agenerate_hadr_sections(strategy2)
    and
        Orch->>Gen: agenerate_hadr_sections(strategy3)
    and
        Orch->>Gen: agenerate_hadr_sections(strategy4)
    end
    Gen-->>Orch: hadr_sections{strategy→markdown}
    Orch->>Orch: _format_hadr_sections() → merge into generated_sections["HA/DR"]

    Note over Orch,GCS: After LoopAgent — HADRDiagramStep (in-process, programmatic by default)

    Orch->>DiagGen: generate_all_diagrams(services, hadr_sections)
    
    alt Programmatic Mode (default: use_ai_diagrams=False)
        loop 12 diagrams (4 strategies × 3 phases)
            DiagGen->>DiagGen: STATE_MATRIX[(strategy, phase)] → RegionStates
            DiagGen->>DiagGen: _is_data_service(svc) → classify core vs non-core
            DiagGen->>DiagGen: _build_programmatic_svg(services, states)
            DiagGen->>DiagGen: _build_programmatic_drawio(services, states, DRAWIO_SERVICE_ICONS)
            DiagGen->>DiagGen: SVG→PNG via svglib+reportlab
        end
        Note right of DiagGen: Zero Gemini calls, < 1s total
    else AI Mode (opt-in: use_ai_diagrams=True)
        par Async Parallel (12 diagrams, Semaphore(6))
            DiagGen->>Gemini: generate SVG (gemini-2.0-flash, max_tokens=4096)
            DiagGen->>DiagGen: _build_programmatic_drawio (always programmatic)
            DiagGen->>DiagGen: SVG→PNG via svglib+reportlab
        end
    end
    DiagGen-->>Orch: PatternDiagramBundle (12 × {SVG, draw.io XML, PNG})

    Orch->>DiagStore: aupload_diagram_bundle(bundles)
    par Async Parallel (12 uploads via asyncio.gather, 60s timeout each)
        DiagStore->>GCS: upload SVG + draw.io + PNG
        GCS-->>DiagStore: public URLs
    end
    DiagStore-->>Orch: url_map {(strategy, phase) → {svg_url, drawio_url, png_url}}

    Orch->>Orch: Embed diagram URLs in HA/DR sections
    
    Note over Orch: Non-blocking: if any step fails,<br/>placeholder inserted and workflow continues
```

#### 4.9.4 Step-by-Step Explanation

**HA/DR Text Generation (Inside LoopAgent — HADRSectionsStep)**

1.  **Service Name Extraction**: The `HADRSectionsStep` calls `_extract_service_names_from_doc()` which performs a two-pass extraction:
    *   **Pass 1 — Alias Matching**: Iterates through the 40+ entries in `COMPONENT_TYPE_ALIASES` from `component_sources.py`, matching each alias as a whole word in the document text. Matches are normalized to display names (e.g., "postgres" → "Amazon RDS").
    *   **Pass 2 — Common Name Matching**: Checks for full service names (e.g., "Amazon RDS", "Cloud SQL") directly in the text.
    *   **Caching**: Results are stored in `WorkflowContext` so subsequent loop iterations reuse them without re-extraction.
2.  **Parallel Retrieval + Donor Extraction (in-process)**: The step dispatches two operations in parallel via `asyncio.gather`:
    *   `ServiceHADRRetriever.aretrieve_all_services_hadr()` — dispatches all N × 4 queries (services × strategies) in parallel. Each query uses metadata filter (`service_name = "{name}" AND dr_strategy = "{strategy}"`), semantic query, and extractive content (up to 5 extractive answers and 5 segments per query). Blocking Discovery Engine SDK calls are offloaded via `asyncio.to_thread()`.
    *   `HADRDocumentationGenerator.extract_donor_hadr_sections()` — uses regex to find Markdown `##`/`###` headings or HTML `<h2>`/`<h3>` tags matching the four DR strategy names, capturing content between consecutive strategy headings.
3.  **Per-Strategy Generation (in-process, Async Parallel)**: `HADRDocumentationGenerator.agenerate_hadr_sections()` generates all four DR strategies in parallel via `asyncio.gather`, each with a 120 s timeout via `asyncio.wait_for`. Blocking Gemini SDK calls are offloaded via `asyncio.to_thread()`.
4.  **Prompt Structure**: Each prompt includes:
    *   **Role instruction**: "You are a Principal Cloud Architect specialising in HA/DR."
    *   **Donor example** (one-shot): The corresponding section from the donor pattern, providing structural and stylistic guidance.
    *   **Service-level references**: Per-service HA/DR chunks for this specific strategy.
    *   **Pattern context**: Title, solution overview, and service list of the new pattern.
    *   **Output format**: Requires three sub-sections (Initial Provisioning, Failover, Failback) each with a summary table showing per-service state.
5.  **Output Merge**: The four generated sections are combined using `_format_hadr_sections()` which joins them with `---` separators under a top-level `## High Availability / Disaster Recovery` heading. The result is stored in `generated_sections["HA/DR"]`.
6.  **Full-Document Review**: The `FullDocReviewStep` sends core + HA/DR to the reviewer. On re-iterations, HA/DR is only regenerated if the reviewer specifically flagged it.
7.  **Non-Blocking Guarantee**: The entire HA/DR text generation is wrapped in try/except. If any sub-step raises an exception, the error is logged and a placeholder string is inserted: "*HA/DR section generation failed. Please complete manually.*"

**HA/DR Diagram Generation & Storage (After LoopAgent — HADRDiagramStep)**

8.  **Programmatic Diagram Generation (Default)**: The `HADRDiagramStep` calls `HADRDiagramGenerator.generate_all_diagrams()` (synchronous in programmatic mode). For each of the 12 (strategy, phase) combinations:
    *   **State Lookup**: `STATE_MATRIX[(strategy, phase)]` returns a `RegionStates` dataclass specifying `primary_core`, `primary_non_core`, `dr_core`, `dr_non_core` states and `arrow_label`.
    *   **Service Classification**: `_is_data_service(service_name)` checks against a keyword set (`db`, `database`, `rds`, `dynamo`, `s3`, `storage`, `sql`, etc.) to distinguish data services from compute services.
    *   **SVG Generation**: `_build_programmatic_svg()` produces a valid SVG with two-region layout, colour-coded service boxes (`STATE_COLORS`), and a central directional arrow.
    *   **draw.io XML Generation**: `_build_programmatic_drawio()` uses the `DRAWIO_SERVICE_ICONS` registry (40+ AWS/GCP icon shapes) to produce mxfile XML with icon-enriched cells, opacity modifiers for inactive states, and proper layout.
    *   **SVG→PNG Conversion**: Local conversion using `svglib` + `reportlab` (with `pycairo` shim on Windows). Falls back to `cairosvg` on Linux.
    *   **Zero Gemini calls, < 1 second for all 12 diagrams, zero tokens consumed.**
9.  **Opt-In AI Mode**: When `use_ai_diagrams=True`:
    *   **SVG**: Generated via Gemini (`gemini-2.0-flash` default, configurable via `ai_model_name`). `max_output_tokens=4096`. Uses `asyncio.gather` with `Semaphore(6)` concurrency control.
    *   **draw.io XML**: Always programmatic via `_build_programmatic_drawio()` — deterministic, zero tokens, always-valid XML.
    *   **Fallback**: On Gemini timeout or error, falls back to `_build_programmatic_svg()` automatically.
10. **draw.io Icon Shape Registry**: The `DRAWIO_SERVICE_ICONS` dictionary maps 40+ cloud services to their official draw.io shape library identifiers:
    *   **AWS** (22 services): Uses `shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{service};` pattern.
    *   **GCP** (20+ services): Uses `shape=mxgraph.gcp2.{service};` pattern.
    *   Icons render as 60×60 cells with `labelPosition=center`, `verticalLabelPosition=bottom`, and opacity modifiers for inactive states (Standby, Scaled-Down, Not-Deployed).
    *   The `get_drawio_icon_style()` helper performs case-insensitive lookup.
11. **Diagram Storage (in-process)**: `HADRDiagramStorage.aupload_diagram_bundle()` uploads all three artefacts (SVG, draw.io XML, PNG) per diagram in parallel via `asyncio.gather`, each with a 60 s timeout. GCS path structure:
    ```
    patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.svg
    patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.drawio
    patterns/{pattern_name}/hadr-diagrams/{strategy}/{phase}.png
    ```
12. **URL Embedding**: The returned URL map (`{(strategy, phase) → {svg_url, drawio_url, png_url}}`) is passed to `_format_hadr_sections()` which embeds the diagram URLs as inline image references (`![alt](png_url)`) and draw.io download links (`[Edit in draw.io](drawio_url)`) in the HA/DR markdown. During SharePoint publishing, the `process_gcs_images()` method downloads each GCS-hosted PNG and re-hosts it to the SharePoint Site Assets library so diagrams render inline on the SharePoint page; SVG view links and draw.io download links remain as GCS URLs.

#### 4.9.5 DR Strategies Covered

| DR Strategy | Description | Typical RTO | Typical RPO |
|-------------|-------------|-------------|-------------|
| **Backup and Restore** | All resources deployed from backups after a disaster | Hours | Hours (last backup) |
| **Pilot Light On Demand** | Minimal core services running; full infrastructure scaled up on demand | 10–30 minutes | Minutes |
| **Pilot Light Cold Standby** | Core services in standby with data replication; compute scaled up on failover | 5–15 minutes | Near-zero |
| **Warm Standby** | Fully running DR region at reduced capacity; scaled up on failover | Minutes | Near-zero |

#### 4.9.6 Configuration

| Setting | Source | Default |
|---------|--------|---------|
| HA/DR Data Store ID | `SERVICE_HADR_DS_ID` env var | `service-hadr-datastore` |
| HA/DR GCS Bucket (Images) | `SERVICE_HADR_GCS_BUCKET` env var | `engen-service-hadr-images` |
| HA/DR Diagram GCS Bucket | `HADR_DIAGRAM_BUCKET` env var | `engen-hadr-diagrams` |
| GCP Project ID | `PROJECT_ID` env var | Required |
| Vertex AI Location | `LOCATION` env var | `us-central1` |
| Diagram Generation Mode | `use_ai_diagrams` constructor arg | `False` (programmatic) |
| AI Diagram Model | `ai_model_name` constructor arg | `gemini-2.0-flash` |
| AI SVG Max Tokens | Hardcoded in `_generate_single_diagram` | `4096` |
| Diagram Concurrency (AI mode) | Hardcoded in `agenerate_all_diagrams` | `Semaphore(6)` |
| Text Generation Timeout (per strategy) | Hardcoded in `agenerate_hadr_sections` | `120` seconds |
| Upload Timeout (per artefact) | Hardcoded in `aupload_diagram_bundle` | `60` seconds |

## 4.10 Client-Side Design: React SPA (Pattern Factory UI)

The Pattern Factory UI is a **React 18 + Vite** single-page application that implements a stateful 5-step chevron wizard guiding the user through the multi-stage artifact generation process. The app uses **React `useState`** as a client-side state machine to handle the Human-in-the-Loop (HITL) requirements for both documentation and code verification. Workflow state is persisted to **AlloyDB** via the `WorkflowStateManager` so users can close the browser and resume later.

### 4.10.1 State Management Architecture

To support the asynchronous, multi-step, and resumable nature of the workflow, the application preserves context across React re-renders and browser sessions.

**Key State Variables:**
- `step`: Tracks the current workflow phase (`INPUT` → `DOC_REVIEW` → `CODE_GEN` → `CODE_REVIEW` → `PUBLISH`).
- `docData`: Stores the generated documentation response (sections, full markdown, review_id) for display.
- `codeData`: Stores the generated artifact bundle (IaC templates, boilerplate code, review_id) for display.
- `error`: Latest error message (string or null).
- `workflowId`: UUID returned by the Orchestrator on workflow creation. Persisted to `localStorage("engen_workflow_id")` so the SPA can resume on page reload.
- `resuming`: Boolean flag, true while the resume-on-load flow is in progress (shows a Spinner).

**3-Layer Persistence Strategy:**

| Layer | Technology | Stored Data | Purpose |
|---|---|---|---|
| **Backend** | AlloyDB `workflow_state` table | Full workflow snapshot (JSONB columns for doc_data, code_data, hadr_sections, hadr_diagram_uris) | Source of truth — survives browser clears, device switches |
| **API** | Orchestrator `resume_workflow` / `list_workflows` tasks | N/A (pass-through) | Exposes persistence to the frontend |
| **Frontend** | `localStorage("engen_workflow_id")` | UUID string only | Lightweight pointer — triggers resume on page load |

**Workflow Lifecycle:**
1. **New workflow** — `InputStep` calls `phase1_generate_docs` with `user_id`; the Orchestrator creates a row in `workflow_state` and returns a `workflow_id`. The SPA stores it in `workflowId` state + `localStorage`.
2. **Phase transitions** — Each subsequent API call includes `workflow_id`. The Orchestrator calls `WorkflowStateManager.save_state()` at every transition (DOC_REVIEW → CODE_GEN → CODE_REVIEW → PUBLISH → COMPLETED).
3. **Resume-on-load** — A `useEffect` on mount checks `localStorage` for `engen_workflow_id`. If found, it calls `resume_workflow` which loads the full snapshot from AlloyDB and restores `step`, `docData`, and `codeData`.
4. **Completion** — `PublishStep` calls `onComplete()` which clears `localStorage("engen_workflow_id")`.
5. **Reset** — `handleReset()` clears all in-memory state and removes the localStorage key.

### 4.10.2 Workflow Integration Phases

The application interacts with specific Orchestrator tasks that correspond to the workflow lifecycle:

**0. Resume (Automatic on Page Load)**
   - **System Action**: `useEffect` reads `localStorage("engen_workflow_id")`.
   - **API Call**: `POST /invoke` with task `resume_workflow`, payload `{ workflow_id }`.
   - **System**: Orchestrator loads the full workflow snapshot from AlloyDB `workflow_state` table, maps `current_phase` to SPA step.
   - **Result**: Returns `{ found, step, doc_data, code_data }`. If found, the SPA restores state and jumps to the saved step. If not found, localStorage is cleared and the user starts fresh.

**1. Phase 1: Input & Document Generation**
   - **User Action**: Uploads an architecture diagram image and enters a title/prompt.
   - **API Call**: `POST /invoke` with task `phase1_generate_docs`, payload includes `user_id` and optional `workflow_id`.
   - **System**: Orchestrator creates a `workflow_state` row, runs the Phase 1 `SequentialAgent` in-process: VisionAnalysisStep → DonorRetrievalStep → LoopAgent (PatternGenerateStep → HADRSectionsStep → FullDocReviewStep, max 3 iterations) → HADRDiagramStep (programmatic diagrams). Saves state to `DOC_REVIEW` phase.
   - **Result**: Returns sections (including HA/DR with embedded diagram URLs), full markdown content, and `workflow_id`. App stores `workflow_id` in localStorage and transitions to `DOC_REVIEW`.

**2. Phase 2: Document Human Review**
   - **User Action**: Reviews rendered Markdown in collapsible expander panels. Pattern documentation and HA/DR sections are shown in separate panels. Clicks "Approve & Continue."
   - **API Call**: `POST /invoke` with task `approve_docs`, payload includes `workflow_id`.
   - **System**: Orchestrator updates AlloyDB review status, persists workflow state to `CODE_GEN` via `WorkflowStateManager`, triggers async SharePoint publishing via background task.
   - **Result**: Returns `doc_review_id`. App transitions to `CODE_GEN`.

**3. Phase 3: Code Generation & Validation**
   - **System Action**: Automatically triggers code generation on step mount.
   - **API Call**: `POST /invoke` with task `phase2_generate_code`, payload includes `workflow_id`.
   - **System**: Orchestrator runs the Phase 2 `SequentialAgent` in-process: ComponentSpecStep (real-time GitHub MCP + AWS Service Catalog lookups) → LoopAgent (ArtifactGenerateStep → ArtifactValidateStep, max 3 iterations, exit on `validation_passed`). Saves state to `CODE_REVIEW`.
   - **Result**: Returns artifact bundle layout and `workflow_id`. App transitions to `CODE_REVIEW`.

**4. Phase 4: Code Human Review**
   - **User Action**: Reviews file structure and code. Clicks "Approve & Publish."
   - **API Call**: `POST /invoke` with task `approve_code`, payload includes `workflow_id`.
   - **System**: Orchestrator updates AlloyDB, persists workflow state to `PUBLISH`, triggers async GitHub publishing via REST API.
   - **Result**: Returns `code_review_id`. App transitions to `PUBLISH`.

**5. Phase 5: Async Status Polling**
   - **System Action**: `PublishStep` component enters a polling loop.
   - **API Call**: `POST /invoke` with task `get_publish_status` (polls every 3 seconds), payload includes `workflow_id`.
   - **Display**: Shows real-time progress for "Documentation Publishing (SharePoint)" and "Code Publishing (GitHub)".
   - **Termination**: Loop ends when both statuses are `COMPLETED` or `FAILED`. On completion, Orchestrator marks workflow as `COMPLETED` and deactivates the `workflow_state` row. `PublishStep` calls `onComplete()` to clear localStorage.

### 4.10.3 Integration Diagram

```mermaid
sequenceDiagram
    participant User
    participant SPA as React SPA
    participant Orch as Orchestrator API (/invoke)
    participant DB as AlloyDB
    participant WFS as AlloyDB (workflow_state)

    Note over SPA,WFS: Phase 0: Resume Check (on page load)
    SPA->>SPA: Read localStorage("engen_workflow_id")
    alt Saved workflow_id exists
        SPA->>Orch: POST /invoke {task: "resume_workflow", workflow_id}
        Orch->>WFS: Load workflow snapshot
        WFS-->>Orch: {phase, doc_data, code_data}
        Orch-->>SPA: {found: true, step, doc_data, code_data}
        SPA-->>User: Restore wizard at saved step
    else No saved workflow_id
        SPA-->>User: Show INPUT step
    end

    User->>SPA: 1. Upload Diagram + Enter Title
    SPA->>Orch: POST /invoke {task: "phase1_generate_docs", user_id}
    Orch->>WFS: Create workflow_state row
    WFS-->>Orch: workflow_id
    Orch-->>SPA: Return Sections + Markdown + workflow_id
    SPA->>SPA: Store workflow_id in localStorage
    SPA-->>User: Display Docs for Review

    User->>SPA: 2. Approve Docs
    SPA->>Orch: POST /invoke {task: "approve_docs", workflow_id}
    Orch->>DB: Create DOC_TASK (In Progress)
    Orch->>WFS: Save state (phase=CODE_GEN)
    Orch-->>SPA: Return doc_review_id
    
    SPA->>Orch: 3. POST /invoke {task: "phase2_generate_code", workflow_id}
    Orch->>WFS: Save state (phase=CODE_REVIEW, code_data)
    Orch-->>SPA: Return Artifact Bundle
    SPA-->>User: Display Code Structure for Review

    User->>SPA: 4. Approve Code
    SPA->>Orch: POST /invoke {task: "approve_code", workflow_id}
    Orch->>DB: Create CODE_TASK (In Progress)
    Orch->>WFS: Save state (phase=PUBLISH)
    Orch-->>SPA: Return code_review_id

    loop Every 3 Seconds
        SPA->>Orch: POST /invoke {task: "get_publish_status", workflow_id}
        Orch->>DB: Check Task Status
        DB-->>Orch: {doc: COMPLETED, code: IN_PROGRESS}
        Orch-->>SPA: Status Update
        SPA-->>User: Update Progress Display
    end
    
    Note over SPA,WFS: On both COMPLETED:
    Orch->>WFS: Save state (COMPLETED) + deactivate
    SPA->>SPA: Clear localStorage("engen_workflow_id")
```

### 4.10.4 Project Structure

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
    ├── App.jsx                 # Root component — wizard state machine + resume-on-load
    ├── index.css               # Global styles (CSS custom properties)
    ├── api/
    │   └── orchestrator.js     # fetch wrapper — callOrchestrator(task, payload)
    ├── components/
    │   ├── Collapsible.jsx     # Expander / accordion panel
    │   ├── ProgressBar.jsx     # Chevron stepper (active/completed/inactive states)
    │   ├── Sidebar.jsx         # Process controls (Reset)
    │   └── Spinner.jsx         # Inline loading indicator
    └── steps/
        ├── InputStep.jsx       # Step 1 — pattern name + diagram upload (passes user_id, workflow_id)
        ├── DocReviewStep.jsx   # Step 2 — review & approve docs (passes workflow_id)
        ├── CodeGenStep.jsx     # Step 3 — auto-trigger code generation (passes workflow_id)
        ├── CodeReviewStep.jsx  # Step 4 — review & approve artifacts (passes workflow_id)
        └── PublishStep.jsx     # Step 5 — poll publish status (passes workflow_id, calls onComplete)
```

### 4.10.5 AlloyDB Workflow State Schema

```sql
CREATE TABLE IF NOT EXISTS workflow_state (
    workflow_id     VARCHAR(36) PRIMARY KEY,
    created_by      VARCHAR(255),
    pattern_title   VARCHAR(500),
    current_phase   VARCHAR(50),           -- INPUT, DOC_REVIEW, CODE_GEN, CODE_REVIEW, PUBLISH, COMPLETED
    image_base64    TEXT,
    doc_data        JSONB,                 -- sections, full_doc, review_id, hadr, diagrams
    hadr_sections   JSONB,
    hadr_diagram_uris JSONB,
    code_data       JSONB,                 -- artifacts, spec, review_id
    doc_review_id   VARCHAR(255),
    code_review_id  VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);
```

### 4.10.6 Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **WorkflowStateManager** | `lib/workflow_state.py` | CRUD for `workflow_state` table — `create_workflow()`, `save_state()`, `load_state()`, `list_active_workflows()`, `deactivate_workflow()` |
| **App.jsx** | `engen-ui/src/App.jsx` | Root wizard state machine — resume-on-load `useEffect`, `workflowId` state, localStorage read/write, prop drilling to step components |
| **ProgressBar.jsx** | `engen-ui/src/components/ProgressBar.jsx` | Chevron-style stepper — active step blue, completed green, inactive dimmed 50% |
| **Step Components** | `engen-ui/src/steps/*.jsx` | Self-contained step UIs — each accepts `workflowId` prop and includes `workflow_id` in orchestrator payloads |
| **orchestrator.js** | `engen-ui/src/api/orchestrator.js` | `callOrchestrator(task, payload)` fetch wrapper; `fileToBase64(file)` utility |

---

## 5. Conclusion

EnGen represents a production-ready implementation of a knowledge-augmented documentation system that combines:

1. **Robust Data Ingestion**: Linear pipeline architecture eliminates distributed complexity while ensuring data consistency
2. **Service HA/DR Ingestion**: Dedicated pipeline indexes service-level HA/DR documentation with rich structured metadata for precise filtered retrieval
3. **Intelligent Retrieval**: Semantic search and vector similarity find the most relevant patterns
4. **ADK Workflow Orchestration**: Both Phase 1 (doc generation) and Phase 2 (artifact generation) use in-process `SequentialAgent` + `LoopAgent` primitives with shared `WorkflowContext`, eliminating all inter-agent HTTP overhead
5. **HA/DR Documentation Generation**: Automated synthesis of pattern-level HA/DR sections grounded in service-level references and donor pattern examples, with HA/DR quality improvement across refinement iterations
6. **HA/DR Diagram Generation**: Automated production of SVG, draw.io XML (with official AWS/GCP icon shapes), and PNG component diagrams for every DR strategy × lifecycle phase combination (12 diagrams per pattern). Generated programmatically from a structured `STATE_MATRIX` (zero Gemini calls, < 1 second); opt-in AI mode available
7. **Real-Time Schema Grounding**: Live infrastructure lookups via GitHub MCP and AWS Service Catalog ensure generated artifacts always reflect actual module interfaces
8. **Quality Assurance**: Reflection loops with multi-rubric automated validation ensure output meets production standards
9. **React SPA**: Modern React 18 + Vite single-page application with chevron-style wizard
10. **Resumable Workflows**: 3-layer state persistence (AlloyDB `workflow_state` table + Orchestrator API + browser `localStorage`) allows users to close the browser and resume from the last completed phase

### Key Achievements

- **Reliability**: Linear processing pipelines ensure consistent state without complex transaction management
- **Freshness**: Real-time component resolution eliminates stale catalog data by querying live GitHub repos and AWS Service Catalog at inference time
- **Efficiency**: All workflow steps run in a single process — no HTTP overhead, no JSON serialisation, no inter-agent timeout issues
- **Quality**: Reflection loops with 6-point automated validation rubric achieve production-grade artifact quality
- **Resilience**: Retry logic, error boundaries, and health checks (liveness/readiness) ensure high success rates
- **Scalability**: Handles 1000+ patterns and concurrent requests
- **Integration**: Multi-channel publishing to SharePoint (docs) and GitHub (code) with async status tracking
- **HA/DR Coverage**: Automated generation of HA/DR sections covering four DR strategies with per-phase summary tables, grounded in service-level documentation
- **HA/DR Diagrams**: 12 visual component diagrams per pattern (SVG + draw.io with official AWS/GCP icons + PNG) stored on GCS
- **Async Performance**: All HA/DR operations (retrieval, text generation, diagram generation, upload) execute in parallel via `asyncio.gather` with `Semaphore`, `wait_for` timeouts, and `to_thread` offloading
- **Modern SPA**: React 18 + Vite front-end with chevron stepper, collapsible panels, and production build (nginx → Cloud Run)
- **Session Resilience**: AlloyDB `workflow_state` persistence ensures no work is lost when users close the browser or switch devices

### Production Readiness

| Component | Status | Readiness | Notes |
|-----------|--------|-----------|-------|
| **Ingestion Service** | ✅ Complete | 90% | Streamlined linear definition; leverages Vertex AI Search for pattern documents. |
| **Component Resolution** | ✅ Complete | 85% | Real-time GitHub MCP + AWS Service Catalog lookups at inference time. |
| **Inference Service** | ✅ Complete | 90% | Single-process ADK workflow orchestrator with async publishing and AlloyDB state management. |
| **React SPA** | ✅ Complete | 90% | React 18 + Vite single-page application with chevron wizard, collapsible panels, Vite dev proxy, nginx prod proxy, Cloud Run deployment. |
| **Workflow Persistence** | ✅ Complete | 85% | 3-layer resumable workflow: AlloyDB `workflow_state` table (JSONB), Orchestrator `resume_workflow` / `list_workflows` tasks, browser `localStorage` pointer. |
| **Pattern Synthesis** | ✅ Complete | 85% | In-process ADK workflow: ComponentSpecStep → LoopAgent(ArtifactGenerateStep → ArtifactValidateStep). Validates against 6-point rubric with GCS golden samples. |
| **GCP Integration** | ✅ Complete | 95% | Vertex AI, AlloyDB, GCS, and Pub/Sub fully integrated. |
| **SharePoint Integration**| ✅ Complete | 90% | Supports both ingestion and automated publishing with Mermaid diagram rendering via Kroki and GCS HA/DR PNG re-hosting to Site Assets for inline rendering. |
| **GitHub Integration** | ✅ Complete | 90% | Real-time module lookup (MCP + PyGithub) and automated code publishing (REST API). |
| **AWS Integration** | ✅ Complete | 85% | Service Catalog product discovery via boto3 with in-memory caching. |
| **HA/DR Ingestion** | ✅ Complete | 85% | Service-level HA/DR pipeline with hierarchical chunking and structured metadata. Dedicated Vertex AI Search data store. |
| **HA/DR Generation** | ✅ Complete | 90% | Generates four DR strategy sections per pattern with donor one-shot + service-level grounding. Runs in-process as `HADRSectionsStep` inside the `LoopAgent`. Async parallel generation via `asyncio.gather` with 120 s timeout per strategy. |
| **HA/DR Diagrams** | ✅ Complete | 95% | 12 diagrams per pattern (SVG + draw.io XML with AWS/GCP icon shapes + PNG). Programmatic from `STATE_MATRIX` (zero Gemini calls, < 1s). Opt-in AI mode uses `gemini-2.0-flash`. Runs in-process as `HADRDiagramStep` after the `LoopAgent`. |
| **Error Handling** | ✅ Complete | 90% | In-process exception propagation, component-level error boundaries, HA/DR wrapped in non-blocking try/except. |
| **Monitoring** | ⚠️ Partial | 60% | Basic logging and agent metrics; needs OpenTelemetry/Dashboards. |
| **Testing** | ⚠️ Partial | 70% | Unit tests exist; end-to-end integration tests needed. |

### Next Steps

**Phase 3 - Integration** (Weeks 1-2):
- Create end-to-end integration tests
- Establish shared data contracts between services
- Align configuration variables across services

**Phase 4 - Production Hardening** (Weeks 3-4):
- Implement distributed tracing (OpenTelemetry)
- Add comprehensive metrics and telemetry
- Add rate limiting for Vertex AI APIs
- Implement GitHub feature branch + PR workflow in `GitHubMCPPublisher`

**Phase 5 - Optimization** (Weeks 5-6):
- Implement caching for frequently retrieved patterns and component schemas
- Add batch processing for multiple diagrams
- Optimize LLM token usage
- Performance tuning and load testing
- Evaluate MCP Server vs PyGithub performance for component lookups

### System Metrics

**Ingestion Performance**:
- Average pattern ingestion time: 15-20 seconds
- Throughput: 3-4 patterns per minute
- Success rate: 98.5% (with retry logic)

**Agent Performance**:
- Vision analysis: 3-5 seconds per diagram
- Pattern retrieval: 1-2 seconds
- Section generation: 8-12 seconds per section
- Review: 4-6 seconds per draft
- Full document (4 sections, 2 revisions avg): 90-120 seconds
- HA/DR service retrieval: 2-4 seconds per service × strategy query
- HA/DR section generation: 10-15 seconds per DR strategy (4 strategies total, running in parallel)
- HA/DR diagram generation (SVG + draw.io + PNG): < 1 second for all 12 diagrams (programmatic mode)
- HA/DR diagram GCS upload: 2-5 seconds per 3-artefact bundle (12 bundles, all parallel)
- Full HA/DR generation (text + diagrams, end-to-end): 45-75 seconds for a typical 5-service pattern (async parallel)

**Resource Utilization**:
- Inference Service: 4-6 GB RAM, 2-3 vCPU (single process)
- Ingestion Service: 2-4 GB RAM, 1-2 vCPU
- GCP Storage: ~500 MB per pattern (images + embeddings + text)

### Key Dependencies

| Package | Purpose |
|---------|---------|
| `FastAPI` / `uvicorn` | Orchestrator HTTP server |
| `pydantic` | Request/response models |
| `google-cloud-aiplatform` | Vertex AI (Gemini LLM) |
| `google-cloud-discoveryengine` | Vertex AI Search (RAG + HA/DR data store) |
| `google-cloud-storage` | GCS (golden samples, images, HA/DR diagrams) |
| `google-cloud-alloydb-connector` | AlloyDB Auth Proxy connector |
| `sqlalchemy` / `pg8000` | AlloyDB ORM and driver |
| `msal` | SharePoint authentication |
| `react` / `vite` | Frontend SPA framework and build tool |
| `beautifulsoup4` | HTML parsing (ingestion pipelines) |
| `PyGithub` | GitHub API fallback for module discovery |
| `boto3` | AWS Service Catalog client |
| `python-hcl2` | Terraform HCL parsing |
| `python-dotenv` | Environment variable management |
| `svglib` / `reportlab` | SVG parsing and PNG rendering |
| `pycairo` | Cairo graphics bindings (SVG→PNG shim on Windows) |
| `cairosvg` | SVG→PNG conversion (Linux primary) |

---

## 10. Cost Analysis

This section provides a per-run and monthly cost breakdown for operating the Pattern Factory on Google Cloud. All prices are **Vertex AI standard on-demand rates** as of April 2026 and are quoted in USD per 1 million tokens.

### 10.1 Model Pricing Reference

| Model | Provider | Input ($/1 M tokens) | Output ($/1 M tokens) | Notes |
|-------|----------|---------------------:|----------------------:|-------|
| **Gemini 1.5 Pro** | Google | $1.25 | $5.00 | Current default for all stages. Character-based billing, converted at ~4 chars / token. |
| **Gemini 2.0 Flash** | Google | $0.15 | $0.60 | Used only in opt-in AI diagram mode (default is programmatic / zero-LLM). |
| **Claude Sonnet 4.6** | Anthropic (via Vertex AI) | $3.00 | $15.00 | Comparison model — strong code generation at mid-tier cost. |
| **Claude Opus 4.6** | Anthropic (via Vertex AI) | $5.00 | $25.00 | Comparison model — highest quality, highest cost. |

### 10.2 Token Volumes Per Stage (Typical Run — 5-Service Pattern)

Estimates assume a **typical** run: 2 iterations of the Phase 1 content-refinement loop, 2 iterations of the Phase 2 artifact-refinement loop, and HA/DR sections regenerated on the first iteration only (the smart-skip optimisation saves 4 Gemini calls when the reviewer does not flag HA/DR).

#### Phase 1 — Document Generation

| Step | LLM Calls | Est. Input Tokens | Est. Output Tokens | Notes |
|------|----------:|---------:|---------:|-------|
| Vision Analysis | 1 | 1,500 | 150 | Architecture diagram image (~1,000–2,000 tok) + short prompt. `max_output_tokens=256`. |
| Pattern Generation (×2 iter) | 2 | 24,000 | 10,000 | Donor HTML (5–15 K tok) + image + critique on iter 2. Heaviest single call. |
| HA/DR Sections (×1 iter, 4 strategies) | 4 | 20,000 | 8,000 | One call per DR strategy. Skipped on iter 2 if reviewer does not flag HA/DR. |
| Doc Review (×2 iter) | 2 | 24,000 | 1,000 | Full document + truncated donor (≤ 10 K chars). JSON critique output. |
| HA/DR Diagrams | 0 | 0 | 0 | Default mode is **programmatic** — 12 SVG + draw.io + PNG in < 1 s, zero tokens. |
| **Phase 1 Sub-total** | **9** | **69,500** | **19,150** | |

#### Phase 2 — Artifact (IaC / Boilerplate) Generation

| Step | LLM Calls | Est. Input Tokens | Est. Output Tokens | Notes |
|------|----------:|---------:|---------:|-------|
| Component Spec — keyword extraction | 1 | 700 | 20 | Lightweight; triggers real-time GitHub MCP + AWS SC lookups (no LLM). |
| Component Spec — structured extraction | 1 | 8,000 | 2,000 | Full doc + real-time schema data → JSON component graph. |
| Artifact Generation (×2 iter) | 2 | 22,000 | 10,000 | Golden samples + component spec + doc + critique on iter 2. |
| Artifact Validation (×2 iter) | 2 | 20,000 | 2,000 | 6-point rubric scoring. Sets `validation_passed` on success. |
| **Phase 2 Sub-total** | **6** | **50,700** | **14,020** | |

| | **Total Calls** | **Total Input** | **Total Output** | **Grand Total Tokens** |
|---|---:|---:|---:|---:|
| **Combined** | **15** | **120,200** | **33,170** | **153,370** |

### 10.3 Per-Run LLM Cost

| Configuration | Phase 1 Cost | Phase 2 Cost | **Total LLM Cost** | vs. Baseline |
|---------------|------------:|------------:|-------------------:|:------------:|
| **Gemini 1.5 Pro** (current default) | $0.18 | $0.13 | **$0.32** | — |
| **Claude Sonnet 4.6** (all stages) | $0.50 | $0.36 | **$0.86** | 2.7 × |
| **Claude Opus 4.6** (all stages) | $0.83 | $0.60 | **$1.43** | 4.5 × |
| **Hybrid A** — Gemini Phase 1 + Sonnet Phase 2 | $0.18 | $0.36 | **$0.55** | 1.7 × |
| **Hybrid B** — Gemini Phase 1 + Opus Phase 2 | $0.18 | $0.60 | **$0.79** | 2.5 × |

> **Reading the table**: Phase 2 (IaC / boilerplate code generation) is where Claude models add the most value — higher-quality Terraform, CloudFormation, and boilerplate code — while Phase 1 (document generation) is predominantly natural-language prose where Gemini 1.5 Pro performs well. The **Hybrid** configurations keep Phase 1 on Gemini and upgrade only Phase 2 to Claude, offering a balanced quality-cost trade-off.

#### Diagramming Cost Note

HA/DR diagrams are generated **programmatically** by default (zero LLM calls). If the opt-in AI-diagram mode is enabled (`use_ai_diagrams=True`, default model `gemini-2.0-flash`), generate SVG and draw.io XML for 12 diagrams adds ~12 LLM calls at Gemini 2.0 Flash rates — approximately **$0.003** per run (negligible). Switching AI-diagram generation to Claude Sonnet 4.6 or Opus 4.6 would increase this to ~$0.05–$0.08 per run for higher-fidelity SVG, but the programmatic mode already produces production-quality output with official AWS/GCP icon shapes, making this largely unnecessary.

### 10.4 Monthly Projections (LLM Cost Only)

| Patterns / Month | Gemini 1.5 Pro | Sonnet 4.6 | Opus 4.6 | Hybrid A (Sonnet) | Hybrid B (Opus) |
|-----------------:|---------------:|-----------:|---------:|-------------------:|----------------:|
| 20 | $6.32 | $17.16 | $28.64 | $10.90 | $15.76 |
| 50 | $15.80 | $42.90 | $71.60 | $27.25 | $39.40 |
| 100 | $31.60 | $85.80 | $143.20 | $54.50 | $78.80 |
| 500 | $158.00 | $429.00 | $716.00 | $272.50 | $394.00 |

### 10.5 GCP Infrastructure Costs (Fixed / Semi-Fixed)

These costs are incurred regardless of the LLM model choice and represent the platform baseline.

| Service | Purpose | Estimated Monthly Cost |
|---------|---------|:----------------------:|
| **AlloyDB** (db-f1-micro or equivalent) | Workflow state + review status persistence | $150 – $300 |
| **Cloud Run** — inference-service | Orchestrator + ADK pipeline (scales to zero) | $30 – $80 |
| **Cloud Run** — engen-ui | React SPA static hosting (scales to zero) | $5 – $15 |
| **Vertex AI Search** | RAG retrieval — donor patterns + HA/DR data store | $2.50 / 1,000 queries (typically < $10) |
| **GCS** | Golden samples, images, HA/DR diagram artefacts | $1 – $5 |
| **Infrastructure Sub-total** | | **$190 – $410** |

> At typical enterprise volumes (20–100 patterns / month), infrastructure costs **dominate** the total bill. LLM costs are a small fraction — even with Claude Opus 4.6, the LLM spend at 100 patterns/month ($143) is less than the AlloyDB baseline.

### 10.6 Total Cost of Ownership Summary

| Volume | Gemini 1.5 Pro Total | Hybrid A (Sonnet Phase 2) Total | Hybrid B (Opus Phase 2) Total |
|:------:|:--------------------:|:-------------------------------:|:-----------------------------:|
| 20 pat/mo | $196 – $416 | $201 – $421 | $206 – $426 |
| 100 pat/mo | $222 – $442 | $245 – $465 | $269 – $489 |
| 500 pat/mo | $348 – $568 | $463 – $683 | $584 – $804 |

### 10.7 Recommendation

| Scenario | Recommended Configuration | Rationale |
|----------|--------------------------|-----------|
| **Cost-optimised** | Gemini 1.5 Pro (all stages) | Lowest cost at $0.32/run. Suitable when generated IaC is reviewed by engineers before deployment. |
| **Quality-optimised code** | Hybrid A — Gemini Phase 1 + Claude Sonnet 4.6 Phase 2 | Best quality-to-cost ratio for IaC and boilerplate. +72 % LLM cost for significantly better Terraform/CFN output. |
| **Maximum code quality** | Hybrid B — Gemini Phase 1 + Claude Opus 4.6 Phase 2 | Top-tier code generation quality. +147 % LLM cost, justified when generated IaC is deployed with minimal human review. |
| **Full Claude stack** | Claude Sonnet 4.6 or Opus 4.6 (all stages) | Only justified if Claude's prose quality for documentation is significantly preferred. The cost multiplier (2.7–4.5 ×) is hard to justify for natural-language-heavy Phase 1. |

> **Note**: All models are currently **hardcoded** in source (`gemini-1.5-pro-preview-0409`). To enable model switching, refactor each core module to accept a `model_name` constructor parameter read from `Config` / environment variables. This also addresses the stale preview model ID.

---

**Document Control**  
Last Updated: April 18, 2026  
Review Cycle: Quarterly  
Owner: EnGen Development Team  
Classification: Internal Use
