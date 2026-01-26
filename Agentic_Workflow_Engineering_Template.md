GCP Multi-Agent RAG Accelerator: Engineering Template
Version: 1.0.0 Status: Production Ready Architecture: Multi-Agent (A2A) with Actor Model Key Features: Hybrid Chunking, Vertex Ranking API, MCP Tooling, Async EvalOps, Harness CI/CD.

1. Template Repository Structure
This directory structure is designed for separation of concerns, scalability, and ease of deployment via modern CI/CD systems.
```bash
gcp-mcp-rag-accelerator/
├── README.md                   # The high-level User Guide (see Section 2 below)  
├── Makefile                    # Shortcuts for local dev, linting, and testing    
│
├── terraform/                  # Infrastructure as Code (IaC)
│   ├── main.tf                 # Entry point linking modules
│   ├── variables.tf            # Global variables (Project ID, Region)
│   └── modules/
│       ├── cloudrun_agents/    # Hosts the Main A2A Service & Eval Worker
│       ├── redis/              # Memorystore for Semantic Caching
│       ├── pubsub/             # Async Eval trace topic & subscription
│       ├── bigquery/           # Datasets for Eval Metrics & Golden Sets
│       └── iam/                # Least-privilege service accounts
│
├── harness/                    # CI/CD Pipeline Definitions
│   ├── pipelines/
│   │   └── evalops_pipeline.yaml # The Dev->PreProd->Prod promotion gate logic    
│   └── templates/
│       └── vertex_eval_step.yaml # Reusable step for running AutoSxS
│
├── config/                     # Environment-specific application configurations  
│   ├── dev.yaml                # e.g., Smaller instance sizes, debug logging      
│   ├── preprod.yaml            # e.g., Production data mirror, strict thresholds  
│   └── prod.yaml               # e.g., High HA, production endpoints
│
├── data_prep/                  # Utilities for data ingestion
│   └── parent_child_indexer.py # Script to convert raw text into JSONL for Hybrid Chunking
│
└── src/                        # Application Source Code
    ├── main.py                 # FastAPI entry point for the Main Agent Service   
    │
    ├── agents/                 # The A2A Core Logic (Actor Model)
    │   ├── base_agent.py       # Abstract base class for event-driven agents      
    │   ├── orchestrator.py     # Primary Agent: Gemini Pro planner, state manager 
    │   ├── retrieval_agent.py  # Deterministic Worker: Wraps the optimized lib    
    │   └── enrichment_agent.py # Reasoning Worker: Gemini Flash MCP Client        
    │
    ├── lib/                    # Shared, Optimized Utilities (The "Secret Sauce") 
    │   ├── async_utils.py      # Decorators for non-blocking I/O
    │   ├── cache_mgr.py        # Unified client for Redis & Vertex Context Caching
    │   ├── vertex_retriever.py # Implements Hybrid Chunking & Ranking API calls   
    │   ├── mcp_client.py       # Generic client for discovering/calling MCP servers
    │   └── tracing.py          # OpenTelemetry setup for distributed agent tracing
    │
    └── eval_worker/            # The Separate Async Evaluation Microservice       
        ├── main.py             # entry point listening to Pub/Sub
        └── judge.py            # Implements Vertex Eval SDK & Custom Rubrics      
```

2. Architectural Diagrams & Descriptions
2.1 End-to-End Component Diagram
```mermaid
graph TD
    %% Styling
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef orchestrator fill:#fff3e0,stroke:#e65100,stroke-width:3px;
    classDef subagent fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px;
    classDef mcp fill:#d1c4e9,stroke:#512da8,stroke-width:2px;
    classDef optimized fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,stroke-dasharray:5 5;
    classDef google fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef async fill:#eceff1,stroke:#546e7a,stroke-width:2px,stroke-dasharray:5 5;

    User([User])
    
    subgraph "Frontend Layer"
        Streamlit["Streamlit UI<br/>(Chat + HITL Feedback)"]:::frontend
    end

    subgraph "Multi-Agent Host Service (Cloud Run)"
        OrchAgent["Primary Orchestrator Agent<br/>(Gemini Pro - Planner)"]:::orchestrator
        Memory[("Short-Term Memory")]:::orchestrator

        %% Agent 2: The Librarian
        subgraph "Retrieval Agent (Deterministic)"
            RetAgent["Retrieval Logic Wrapper"]:::subagent
            AsyncCtrl["Async Controller"]:::optimized
            Redis[("Redis Semantic Cache")]:::optimized
        end

        %% Agent 3: The Researcher
        subgraph "Enrichment Agent (Reasoning)"
            EnrichAgent["Enrichment Agent<br/>(Gemini Flash)"]:::subagent
            MCPClient["MCP Client"]:::mcp
        end
    end

    subgraph "External Tooling"
        MCPServer["MCP ServerHost<br/>(e.g. APIs)"]:::mcp
    end

    subgraph "Google Cloud Services (Runtime)"
        VertexSearch["Vertex AI Search<br/>(Hybrid Store)"]:::google
        RankingAPI["Vertex AI Ranking API"]:::google
        ContextCache["Vertex AI Context Cache"]:::google
        VertexLLM["Vertex AI LLM API"]:::google
    end

    subgraph "EvalOps Layer (Asynchronous)"
        PubSub{"Pub/Sub<br/>Trace Topic"}:::async
        EvalWorker["Eval Worker Service"]:::async
        VertexEval["Vertex AI Eval API<br/>(Judge + Rubric)"]:::google
        BigQuery[("BigQuery<br/>Metrics Store")]:::async
    end

    %% Flows
    User <--> Streamlit
    Streamlit <-->|Async| OrchAgent
    OrchAgent <--> Memory

    %% A2A Delegation
    OrchAgent -- "1. Fetch" --> RetAgent
    RetAgent -- "2. Context" --> OrchAgent
    OrchAgent -- "3. Enrich" --> EnrichAgent
    EnrichAgent -- "4. Data" --> OrchAgent
    OrchAgent -- "5. Synthesize" --> VertexLLM

    %% Optimization Internals
    RetAgent --> AsyncCtrl
    AsyncCtrl --> Redis
    AsyncCtrl --> VertexSearch
    AsyncCtrl --> RankingAPI
    AsyncCtrl --> ContextCache

    %% MCP Flow
    EnrichAgent --> MCPClient --> MCPServer

    %% Eval Flow
    OrchAgent -.->|Fire-and-Forget Trace| PubSub
    PubSub -.-> EvalWorker
    EvalWorker -.-> VertexEval
    VertexEval -.-> BigQuery
    Streamlit -.->|HITL Feedback| BigQuery
```
Description: This diagram represents a microservices-based Multi-Agent architecture hosted on Google Cloud Run.

The Orchestrator: Acts as the central brain (Manager), holding conversation state and delegating tasks. It never accesses data directly.

Retrieval Agent: A specialized worker that encapsulates the "Optimized RAG" logic (Hybrid Search + Ranking + Caching). It is deterministic code, not an LLM.

Enrichment Agent: An LLM-based worker that uses the Model Context Protocol (MCP) to discover and call external APIs (like stock prices or weather) to augment the retrieved text.

EvalOps Layer: A completely decoupled, asynchronous pipeline where a dedicated "Eval Worker" listens to Pub/Sub events to score responses against rubrics without slowing down the user.

2.2 End-to-End Sequence Diagram
```mermaid

sequenceDiagram
    autonumber
    actor User
    participant UI as Streamlit UI
    participant Orch as Primary Orchestrator
    participant Redis as Redis Cache
    participant RetAgent as Retrieval Agent
    participant Enrich as Enrichment Agent
    participant MCP as MCP Server
    participant Google as Vertex AI (Search/Rank/LLM)
    participant PubSub as Pub/Sub (Trace Topic)
    participant Eval as Eval Worker Service
    participant BQ as BigQuery (Metrics)

    User->>UI: Query: "Analysis of T-100 specs?"
    UI->>Orch: Submit Query (Start Trace)

    %% --- PHASE 1: CACHE CHECK (The Fast Path) ---
    Orch->>Redis: Check Semantic Cache(query_vector)
    
    alt Cache HIT
        Redis-->>Orch: Return Cached Answer
        Orch-->>UI: Stream Cached Answer
    else Cache MISS
        Note right of Orch: Start Agentic Workflow
        
        %% --- PHASE 2: OPTIMIZED RETRIEVAL ---
        Orch->>RetAgent: Call(query)
        RetAgent->>Google: 1. Hybrid Search (50 Candidates)
        Google-->>RetAgent: Return Parent Metadata
        RetAgent->>Google: 2. Ranking API (Top 5)
        Google-->>RetAgent: Return High-Value Context
        RetAgent-->>Orch: Return Context

        %% --- PHASE 3: ENRICHMENT (MCP) ---
        Orch->>Enrich: Call(query, context)
        Enrich->>Google: Reason("Need external tools?")
        Google-->>Enrich: "Yes, check warranty status"
        Enrich->>MCP: List & Call Tool(get_warranty)
        MCP-->>Enrich: {warranty: "Active"}
        Enrich-->>Orch: Return Enriched Data

        %% --- PHASE 4: GENERATION ---
        Orch->>Google: Generate Final Answer (Pro)
        Google-->>Orch: Stream Tokens
        
        par Async Operations
            Orch-->>UI: Stream Response to User
            Orch->>Redis: Update Cache(query, answer)
            Orch-)PubSub: Publish Trace Event {Query, Response, Context}
        end
    end

    %% --- PHASE 5: ASYNC EVAL & HITL TRIGGER ---
    Note over PubSub, BQ: Asynchronous Evaluation Loop
    
    PubSub-)Eval: Consume Trace
    Eval->>Google: Run Vertex AutoSxS (Judge)
    Google-->>Eval: Score (Faithfulness: 0.75)
    
    Eval->>Eval: Check Threshold (Threshold = 0.85)
    
    alt Score < Threshold (Low Confidence)
        Note right of Eval: TRIGGER HITL
        Eval->>BQ: Insert Row (Status="NEEDS_HUMAN_REVIEW")
        Eval-)UI: (Optional) Push "Request Feedback" Notification
    else Score >= Threshold
        Eval->>BQ: Insert Row (Status="PASS")
    end
```
Description: This detailed flow breakdown highlights exactly where each engineering optimization (Caching, Async, MCP, EvalOps) is executed in the runtime path.

### Phase 1: Initiation & The "Zero-Latency" Check

* **Step 1:** The **User** submits a query (e.g., "Analysis of T-100 specs?") via the **Streamlit UI**.
* **Step 2:** The UI sends the request asynchronously to the **Primary Orchestrator Agent** running on Cloud Run. A distributed trace ID is generated here to track the request across all microservices.
* **Step 3:** **(Semantic Caching)** The Orchestrator immediately hashes the query and checks **Redis** for a semantic match. This is the "Fast Path" designed to return an answer in <100ms if the question has been asked before.
* **Step 4:** **(Cache Hit Scenario)** If a match is found (Similarity > 0.95), Redis returns the stored answer immediately.
* **Step 5:** The Orchestrator streams this cached response back to the UI, bypassing all subsequent expensive steps.

### Phase 2: Optimized Retrieval (The "Librarian")

* **Step 6:** **(Cache Miss)** If Redis returns null, the Orchestrator delegates the task to the **Retrieval Agent**. This is a deterministic code block, not an LLM.
* **Step 7:** **(Hybrid Chunking)** The Retrieval Agent executes a search against **Vertex AI Search**. It uses a high-precision query against 100-token "Child" chunks but requests the return of the 500-token "Parent" metadata.
* **Step 8:** Vertex AI returns ~50 candidate Parent chunks. This is a "wide" fetch to ensure recall.
* **Step 9:** **(Context Compression)** The Agent sends these 50 candidates to the **Vertex AI Ranking API**.
* **Step 10:** The Ranking API uses a cross-encoder model to score relevance and discards the bottom 45 chunks, returning only the **Top 5 High-Value Chunks**.
* **Step 11:** **(Context Caching)** If these 5 chunks exceed a token threshold (e.g., >10k tokens), the Agent registers them with **Vertex AI Context Cache** to reduce future latency. It returns the `Context_ID` (or raw text) to the Orchestrator.

### Phase 3: Enrichment (The "Researcher")

* **Step 12:** The Orchestrator passes the query and the retrieved context to the **Enrichment Agent**.
* **Step 13:** **(Reasoning)** The Enrichment Agent asks **Gemini 1.5 Flash** (optimized for speed) if the current context is sufficient or if external tools are needed.
* **Step 14:** Gemini Flash reasons: "The user asked for *current* warranty status, which is not in the static docs. Yes, use a tool."
* **Step 15:** **(MCP Discovery)** The Agent uses the **Model Context Protocol (MCP)** to query the **MCP Server** for available tools (`list_tools`).
* **Step 16:** **(MCP Execution)** The Agent dynamically calls the `get_warranty` tool on the MCP Server.
* **Step 17:** The MCP Server returns the live structured data (e.g., `{warranty: "Active", expires: "2027"}`), which is returned to the Orchestrator.

### Phase 4: Generation & Async Write-Back

* **Step 18:** The Orchestrator sends the prompt (System Instructions + Optimized Context + Live MCP Data) to **Gemini 1.5 Pro**.
* **Step 19:** **(Streaming)** Gemini 1.5 Pro begins streaming tokens immediately (Time-to-First-Token).
* **Step 20:** The Orchestrator forwards these tokens to the **Streamlit UI** via Server-Sent Events (SSE) so the user sees the answer being typed out in real-time.
* **Step 21:** **(Async Write)** Simultaneously (without blocking the stream), the Orchestrator updates **Redis** with the new Query-Response pair for future semantic hits.
* **Step 22:** **(Async Trace)** The Orchestrator fires a "fire-and-forget" event to **Pub/Sub** containing the full interaction trace. This concludes the user-facing latency path.

### Phase 5: EvalOps & Human-in-the-Loop (The Background Worker)

* **Step 23:** The **Eval Worker Service** consumes the trace event from Pub/Sub.
* **Step 24:** The Worker calls the **Vertex AI Evaluation API**, triggering an AutoSxS (Side-by-Side) task or a custom rubric check.
* **Step 25:** **(The Judge)** The Vertex AI "Judge" model scores the response (e.g., Faithfulness: 0.75, Relevance: 0.9).
* **Step 26:** The Worker compares this score against the pre-defined **Quality Threshold** (e.g., 0.85).
* **Step 27:** **(HITL Trigger)** Since 0.75 < 0.85, the Worker flags this transaction.
* **Step 28:** The Worker inserts a record into **BigQuery** with the status `NEEDS_HUMAN_REVIEW`.
* **Step 29:** (Optional) The Worker pushes a notification back to the frontend or an admin dashboard, signaling that this specific response requires human verification or user feedback to improve the Golden Dataset.

2.3 DevSecOps Pipeline Diagram (Harness)
```mermaid
graph LR
    subgraph "Harness CI/CD Pipeline"
        
        subgraph "Dev (Commit)"
            Commit[Git Push] --> Build[Build Container]
            Build --> DeployDev[Deploy to Dev]
            DeployDev --> Smoke["Run Vertex Rapid Eval<br/>(Sanity Check)"]
        end

        Smoke --> Gate1{Pass Smoke?}
        
        subgraph "Pre-Prod (Merge)"
            Gate1 -- Yes --> Merge[Merge to Main]
            Merge --> DeployPre["Deploy to Pre-Prod<br/>(Prod Mirror)"]
            DeployPre --> DeepEval["Run AutoSxS Eval<br/>(Golden Dataset)"]
        end

        DeepEval --> Gate2{Faithfulness > 0.9?}

        subgraph "Prod (Release)"
            Gate2 -- Yes --> Canary["Canary Deploy (10%)"]
            Canary --> Rollout[Full Rollout]
        end

        Gate2 -- No --> Block[Block & Alert]
    end
```
Description: This pipeline enforces quality at every stage.

Dev: Runs a fast "Smoke Test" (Rapid Eval) to ensure the agent isn't broken (e.g., returning JSON errors).

Pre-Prod: The critical gate. Runs a "Deep Eval" using Vertex AI AutoSxS against a Golden Dataset. This compares the new model's answers against a baseline.

Quality Gate: Harness specifically checks the numeric scores (Faithfulness > 0.9). If failed, Production deployment is blocked automatically.

3. Infrastructure as Code (Terraform Modules)
3.1 terraform/modules/cloudrun_agents/main.tf
Deploys the main Agent Service and the background Eval Worker.

```hcl

resource "google_cloud_run_service" "main_agent_service" {
  name     = "agent-service-${var.env}"
  location = var.region

  template {
    spec {
      containers {
        image = var.container_image
        env {
          name = "ENV_TYPE"
          value = var.env
        }
        env {
          name = "REDIS_HOST"
          value = var.redis_host
        }
        # Connection to Pub/Sub for Eval traces
        env {
          name = "PUBSUB_TOPIC_ID"
          value = var.pubsub_topic
        }
      }
    }
  }
}

resource "google_cloud_run_service" "eval_worker" {
  name     = "eval-worker-${var.env}"
  location = var.region

  template {
    spec {
      containers {
        image = var.worker_image
        # Worker config
      }
    }
  }
}
```
3.2 terraform/modules/redis/main.tf
Provisions Memorystore for the Semantic Cache.

```hcl

resource "google_redis_instance" "cache" {
  name           = "agent-cache-${var.env}"
  memory_size_gb = 1
  region         = var.region
  redis_version  = "REDIS_6_X"
  display_name   = "Agent Semantic Cache (${var.env})"
}

output "host" {
  value = google_redis_instance.cache.host
}
```
3.3 terraform/modules/pubsub/main.tf
Sets up the async trace pipeline.

```hcl

resource "google_pubsub_topic" "agent_traces" {
  name = "agent-traces-${var.env}"
}

resource "google_pubsub_subscription" "eval_worker_sub" {
  name  = "eval-worker-sub-${var.env}"
  topic = google_pubsub_topic.agent_traces.name
  
  # Push config to Cloud Run worker
  push_config {
    push_endpoint = "${var.eval_worker_url}/process_trace"
    oidc_token {
      service_account_email = var.invoker_sa_email
    }
  }
}
```
3.4 terraform/modules/bigquery/main.tf
Creates the datasets for Golden Sets and Runtime Metrics.

```hcl

resource "google_bigquery_dataset" "eval_ops" {
  dataset_id                  = "agent_eval_ops_${var.env}"
  friendly_name               = "Agent Evaluation Metrics"
  description                 = "Stores AutoSxS results, Runtime Traces, and Golden Datasets"
  location                    = "US"
  default_table_expiration_ms = null
}

resource "google_bigquery_table" "metrics" {
  dataset_id = google_bigquery_dataset.eval_ops.dataset_id
  table_id   = "runtime_metrics"
  schema     = file("${path.module}/schemas/metrics_schema.json")
}
```
3.5 terraform/modules/iam/main.tf
Defines the Service Accounts for the agents.

```hcl

resource "google_service_account" "agent_sa" {
  account_id   = "agent-runner-${var.env}"
  display_name = "Agent Service Runner"
}

# Grant Vertex AI User
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Grant Discovery Engine (Search) User
resource "google_project_iam_member" "search_user" {
  project = var.project_id
  role    = "roles/discoveryengine.editor"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}
```
4. Harness Pipeline Definitions
4.1 harness/pipelines/evalops_pipeline.yaml
The master pipeline logic.

```yaml

pipeline:
  name: GCP-Agentic-RAG-EvalOps
  identifier: Agentic_RAG_EvalOps
  projectIdentifier: Default_Project
  orgIdentifier: default
  tags: {}
  stages:
    - stage:
        name: Dev Smoke Test
        identifier: Dev_Smoke_Test
        type: CI
        spec:
          cloneCodebase: true
          execution:
            steps:
              - step:
                  type: Run
                  name: Vertex Rapid Eval
                  identifier: Vertex_Rapid_Eval
                  spec:
                    connectorRef: account.gcp_connector
                    image: python:3.9
                    command: python scripts/run_rapid_eval.py --env dev --limit 20
    
    - stage:
        name: PreProd Deep Eval
        identifier: PreProd_Deep_Eval
        type: CD
        spec:
          serviceConfig:
            serviceRef: agent_service_preprod
          execution:
            steps:
              - step:
                  type: K8sRollingDeploy # Or CloudRunDeploy
                  name: Deploy PreProd
                  identifier: Deploy_PreProd
              
              - step:
                  name: AutoSxS Evaluation
                  identifier: AutoSxS_Eval
                  template:
                    templateRef: vertex_eval_step # Uses the template below
                    templateInputs:
                      golden_dataset: "bq://my-proj.eval.golden_set_v2"
    
    - stage:
        name: Production Gate
        identifier: Production_Gate
        type: Approval
        spec:
          execution:
            steps:
              - step:
                  type: HarnessApproval
                  spec:
                    approvers:
                      userGroups: ["AI_Engineers"]
                    policy:
                      rego: |
                        package pipeline
                        deny[msg] {
                          input.stages.PreProd_Deep_Eval.output.faithfulness < 0.90
                          msg := "Faithfulness below 90%. Deployment Blocked."
                        }
```
4.2 harness/templates/vertex_eval_step.yaml
Reusable template for running Google's evaluation.

```yaml

template:
  name: Vertex AutoSxS Step
  identifier: vertex_eval_step
  type: Step
  spec:
    type: Run
    spec:
      connectorRef: account.gcp_connector
      image: google/cloud-sdk:latest
      command: |
        echo "Starting Vertex AI AutoSxS Evaluation..."
        gcloud ai evaluation-tasks create \
          --display-name="eval-pipeline-${HARNESS_BUILD_ID}" \
          --dataset="<+input.golden_dataset>" \
          --metric-specs="faithfulness,answer_relevance" \
          --output-uri="bq://my-proj.eval.results"
      outputVariables:
        - name: faithfulness
        - name: answer_relevance
```
5. Configuration Files
5.1 config/dev.yaml
```yaml

environment: "dev"
debug_mode: true
log_level: "DEBUG"

vertex:
  search_datastore_id: "docs-ds-dev"
  project_id: "acme-ai-dev"
  location: "global"

agents:
  retrieval:
    top_k_search: 10
    enable_ranking: false # Save cost in dev
  enrichment:
    mcp_servers:
      - name: "mock-tools"
        url: "http://mock-mcp:8080"
```
5.2 config/prod.yaml
```yaml

environment: "prod"
debug_mode: false
log_level: "INFO"

vertex:
  search_datastore_id: "docs-ds-prod"
  project_id: "acme-ai-prod"
  location: "global"

agents:
  retrieval:
    top_k_search: 50
    enable_ranking: true # Critical for quality
    ranking_model: "semantic-ranker-512@latest"
  enrichment:
    mcp_servers:
      - name: "finance-api"
        url: "https://finance-mcp.internal"
      - name: "weather-api"
        url: "https://weather-mcp.internal"
```
6. Data Preparation
6.1 data_prep/parent_child_indexer.py
Utility to chunk data for the Hybrid Chunking strategy.

```python

import json
import argparse

def chunk_text(text, chunk_size, overlap):
    # TODO: Implement robust sliding window tokenizer
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", required=True)
    parser.add_argument("--output_file", required=True)
    args = parser.parse_args()

    with open(args.input_file, 'r') as f_in, open(args.output_file, 'w') as f_out:
        raw_data = f_in.read()
        
        # 1. Create Parent Chunk (Context)
        parent_chunks = chunk_text(raw_data, 2000, 200) # 2000 chars ~ 500 tokens
        
        for p_idx, parent in enumerate(parent_chunks):
            # 2. Create Child Chunks (Search Targets)
            child_chunks = chunk_text(parent, 400, 50) # 400 chars ~ 100 tokens
            
            for c_idx, child in enumerate(child_chunks):
                record = {
                    "id": f"doc_{p_idx}_child_{c_idx}",
                    "content": child, # Indexed for search
                    "structData": {
                        "parent_context": parent, # Retrieved payload
                        "source": args.input_file
                    }
                }
                f_out.write(json.dumps(record) + "\n")

if __name__ == "__main__":
    main()
```
7. Source Code (src/)
7.1 src/main.py
FastAPI Entry Point.

```python

from fastapi import FastAPI, BackgroundTasks
from src.agents.orchestrator import OrchestratorAgent
from src.lib.tracing import setup_tracing

app = FastAPI()
setup_tracing(app)

# Initialize Singleton Agent
orchestrator = OrchestratorAgent()

@app.post("/query")
async def chat_endpoint(query_request: dict, background_tasks: BackgroundTasks):
    user_query = query_request.get("query")
    
    # Execute A2A Workflow
    response, trace_data = await orchestrator.execute(user_query)
    
    # Fire-and-forget Eval Trace (Async)
    background_tasks.add_task(orchestrator.publish_trace, trace_data)
    
    return {"answer": response}
```
7.2 src/agents/base_agent.py
Abstract Base Class.

```python

from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, *args, **kwargs):
        """Core logic for the agent."""
        pass
```
7.3 src/agents/orchestrator.py
The "Manager" agent.

```python

from src.agents.base_agent import BaseAgent
from src.agents.retrieval_agent import RetrievalAgent
from src.agents.enrichment_agent import EnrichmentAgent
from vertexai.generative_models import GenerativeModel
# Custom Libs
from src.lib.tracing import trace_span

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Orchestrator")
        self.model = GenerativeModel("gemini-1.5-pro-001")
        self.retriever = RetrievalAgent()
        self.enricher = EnrichmentAgent()
        
    @trace_span("orchestrator_execution")
    async def execute(self, query: str):
        # 1. Delegation: Retrieval
        context_data = await self.retriever.execute(query)
        
        # 2. Delegation: Enrichment (with MCP)
        enriched_data = await self.enricher.execute(query, context_data)
        
        # 3. Synthesis
        prompt = f"""
        Answer the user query based on the context and live data.
        Query: {query}
        Context: {context_data}
        Live Data: {enriched_data}
        """
        response = await self.model.generate_content_async(prompt)
        
        # Prepare Trace Data for Eval
        trace_payload = {
            "query": query,
            "response": response.text,
            "context": context_data
        }
        
        return response.text, trace_payload

    async def publish_trace(self, trace_data):
        # Use PubSub client to push to 'agent-traces' topic
        pass 
```
7.4 src/agents/retrieval_agent.py
Wrapper for the optimized library.

```python

from src.agents.base_agent import BaseAgent
from src.lib.vertex_retriever import VertexRetriever
from src.lib.tracing import trace_span

class RetrievalAgent(BaseAgent):
    def __init__(self):
        super().__init__("RetrievalAgent")
        self.lib = VertexRetriever() # Handles the heavy lifting

    @trace_span("retrieval_agent_execution")
    async def execute(self, query: str):
        # This is a deterministic agent (Tool Wrapper)
        # It calls the optimized pipeline
        return await self.lib.search_rank_and_cache(query)
```
7.5 src/agents/enrichment_agent.py
The "Reasoning" agent using MCP.

```python

from src.agents.base_agent import BaseAgent
from src.lib.mcp_client import MCPClient
from vertexai.generative_models import GenerativeModel
from src.lib.tracing import trace_span

class EnrichmentAgent(BaseAgent):
    def __init__(self):
        super().__init__("EnrichmentAgent")
        self.flash_model = GenerativeModel("gemini-1.5-flash-001")
        self.mcp = MCPClient()

    @trace_span("enrichment_reasoning")
    async def execute(self, query, context):
        # 1. Reason: Do we need a tool?
        decision_prompt = f"Given query '{query}' and context, do we need external tools? YES/NO"
        resp = await self.flash_model.generate_content_async(decision_prompt)
        
        if "YES" in resp.text:
            # 2. Discovery
            tools = await self.mcp.list_tools()
            # TODO: Logic to select best tool from list
            
            # 3. Execution
            result = await self.mcp.call_tool("get_stock_price", {"ticker": "GOOG"})
            return result
            
        return "No external data needed."
```
8. Library (src/lib/)
8.1 src/lib/async_utils.py
```python

import asyncio
import functools

def async_timer(func):
    """Decorator to log execution time of async functions."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Implementation placeholder
        return await func(*args, **kwargs)
    return wrapper
```
8.2 src/lib/cache_mgr.py
Handles Redis and Context Caching.

```python

import redis.asyncio as redis
from google.cloud import aiplatform

class CacheManager:
    def __init__(self, host, port=6379):
        self.redis = redis.Redis(host=host, port=port)

    async def get_semantic_hit(self, embedding_vector):
        # TODO: Implement vector similarity search within Redis (RediSearch)
        return None

    async def create_vertex_context_cache(self, content: str):
        # TODO: Call Vertex AI SDK to create a CachedContent object
        # Return resource ID
        return "projects/.../locations/.../cachedContents/12345"
```
8.3 src/lib/vertex_retriever.py (The Core Engine)
Implements Hybrid Chunking and Ranking.

```python

from google.cloud import discoveryengine_v1alpha as discoveryengine

class VertexRetriever:
    def __init__(self):
        # Initialize clients
        pass

    async def search_rank_and_cache(self, query):
        """
        1. Search (Top 50 Child Chunks)
        2. Extract Parent from structData
        3. Rank (Top 5 Parents)
        """
        # Placeholder for discoveryengine client calls
        # See section 3.2 in user guide for full logic
        return ["Optimized Context Chunk 1", "Optimized Context Chunk 2"]
```
8.4 src/lib/mcp_client.py
Generic MCP Tooling.

```python

import httpx

class MCPClient:
    def __init__(self, server_url="http://localhost:8080"):
        self.base_url = server_url

    async def list_tools(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/tools")
            return resp.json()

    async def call_tool(self, tool_name, args):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/tools/{tool_name}/call", json=args)
            return resp.json()
```
8.5 src/lib/tracing.py
OpenTelemetry Boilerplate.

```python

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

def setup_tracing(app):
    trace.set_tracer_provider(TracerProvider())
    # Configure Google Cloud Trace exporter
    pass

def trace_span(name):
    # Decorator to create spans
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
```
9. Eval Worker (src/eval_worker/)
9.1 src/eval_worker/main.py
Pub/Sub Listener.

```python

from fastapi import FastAPI, Request
from src.eval_worker.judge import evaluate_trace

app = FastAPI()

@app.post("/process_trace")
async def process_trace_event(request: Request):
    # Unwrap Pub/Sub message
    envelope = await request.json()
    message = envelope.get("message", {})
    trace_data = message.get("data") # Base64 decoded
    
    # Run Evaluation
    await evaluate_trace(trace_data)
    
    return {"status": "ok"}
```
9.2 src/eval_worker/judge.py
Vertex Eval SDK + Rubrics.

```python

from vertexai.preview.evaluation import EvalTask, MetricPromptTemplateExamples

async def evaluate_trace(trace_json):
    """
    1. Parse Trace (Query, Response, Context)
    2. Run Vertex Eval (Groundedness)
    3. Run Custom Rubric (LLM as Judge)
    4. Write to BigQuery
    """
    # TODO: Initialize EvalTask with "faithfulness" and "answer_relevance"
    
    # Custom Rubric Example
    rubric = "Score 1-5. Did the agent explicitly mention the disclaimer?"
    
    # Insert results into BigQuery
    pass
```