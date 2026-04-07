# Ingestion Pipelines — A Plain English Walkthrough

EnGen has **two active ingestion pipelines** and **one retired (legacy) pipeline**. Their job is to take raw knowledge from various sources and load it into searchable data stores so the Pattern Factory agents can find it later.

Think of ingestion as "stocking the shelves" — you do it ahead of time so that when an agent needs information, it's already sitting there, indexed and ready to search.

---

## Pipeline 1 — Vertex Search Pipeline (Pattern Documents)

**What it does:** Takes architecture pattern pages from SharePoint and loads them into **Vertex AI Search** (Google's managed search engine) so the Retrieval Agent can find similar patterns later.

**Source file:** `ingestion-service/pipelines/vertex_search_pipeline.py`

### Before It Runs — Setup

1. The pipeline needs credentials for three things:
   - **SharePoint** (via Azure AD Client Credentials) — to read pattern pages.
   - **Google Cloud Storage** (via GCP Service Account) — to store images permanently.
   - **Vertex AI** (via Application Default Credentials) — to call the Gemini AI model and the search indexing API.

2. It initializes **Gemini 1.5 Flash** — a fast, cheap AI model that can understand images. This is used to "read" architecture diagrams and describe them in words.

### How It Works — Step by Step

3. **Fetch the pattern catalog.** The pipeline calls the SharePoint Client, which talks to the Microsoft Graph API to get a list of all architecture patterns stored in a SharePoint List. Each item has metadata like Title, Owner, Maturity Level, and a link to the full documentation page.

4. **Loop through each pattern.** For each one, the pipeline runs these steps:

5. **Download the HTML page.** The SharePoint Client fetches the raw HTML content of the pattern's documentation page. SharePoint stores the content in a hidden field called `CanvasContent1` — the client knows how to extract this.

6. **Find the diagrams.** The pipeline uses `BeautifulSoup` (an HTML parser) to find all `<img>` tags. It only processes the **first two images**, because in the company's SharePoint template, Image 1 is always the **Component Diagram** and Image 2 is always the **Sequence Diagram**. Other images (logos, icons) are skipped.

7. **Describe each diagram using AI.** For each of the two diagrams:
   - The pipeline downloads the image bytes from SharePoint.
   - It sends those bytes to **Gemini 1.5 Flash** with the prompt: *"Analyze this technical architecture diagram. Provide a detailed textual description of the components, relationships, and flow depicted."*
   - The AI returns a text description like: *"A three-tier architecture with an Application Load Balancer forwarding traffic to an ECS Fargate cluster, backed by an RDS PostgreSQL database in a Multi-AZ configuration."*

8. **Upload images to GCS.** The original images are uploaded to a Google Cloud Storage bucket (so we have a permanent, reliable URL instead of a SharePoint link that might break). The path is `patterns/{pattern_id}/images/diag_0.png`.

9. **Rewrite the HTML.** The pipeline updates the `<img>` tags in the HTML:
   - Replaces the `src` attribute with the new GCS URL.
   - Sets the `alt` text to the AI-generated description (for accessibility and searchability).

10. **Inject descriptions into the page.** The pipeline creates a new HTML section at the top of the document — a `<div>` with class `ai-generated-context` — and pastes the full AI descriptions there. **Why?** Because when Vertex Search creates embeddings (mathematical representations) of the document, it reads the text. If a diagram shows a "load balancer" but the word "load balancer" never appears in the text, the search engine wouldn't know about it. By injecting the description, the visual knowledge becomes searchable.

11. **Map metadata.** The pipeline takes SharePoint list fields (Title, Owner, Maturity, Status, Category, etc.) and maps them to a `struct_data` dictionary. This is used for **filtering** in Vertex Search (e.g., "show me only Production-maturity patterns").

12. **Index the document.** The pipeline sends both the enriched HTML and the metadata to Vertex AI Search using the `write_document` API. The search engine handles chunking (splitting the text into pieces), embedding (turning text into vectors), and indexing (making it searchable). If the document already exists, it's updated in place (upsert).

### Error Handling

- If one pattern fails (e.g., SharePoint page not found), the error is logged and the pipeline **moves on** to the next pattern. It doesn't crash the entire batch.
- The SharePoint Client has built-in retry logic with exponential backoff for HTTP 429 (rate limiting) and 503 (temporary failures).
- Tokens are auto-refreshed before they expire (checked every request), so the pipeline can run for hours without authentication issues.

---

## Pipeline 2 — Service HA/DR Ingestion Pipeline

**What it does:** Takes per-service HA/DR documentation from SharePoint (one page per cloud service like "Amazon RDS" or "AWS Lambda") and loads it into a **separate, dedicated** Vertex AI Search data store called `service-hadr-datastore`. This is used later by the HA/DR generation agents to write disaster recovery sections.

**Why it's separate:** Pattern documents and HA/DR documents serve completely different purposes. Keeping them in separate data stores prevents cross-contamination — you don't want a search for "RDS failover" to accidentally return an unrelated architecture pattern that mentions RDS.

### How It Works — Step by Step

1. **Read the service list from SharePoint.** The pipeline calls `fetch_service_hadr_list()` on the SharePoint Client — exactly the same pattern used by Pipeline 1's `fetch_pattern_list()`. This reads a **dedicated SharePoint List** (identified by the `SP_HADR_LIST_ID` environment variable) whose columns include `ServiceName`, `ServiceDescription`, `ServiceType` (Compute, Storage, Database, Network), and `HADRPageLink` (a hyperlink to the service’s HA/DR page). Pagination is handled automatically. No local JSON file is needed.

2. **Fetch the HTML page for each service.** Same mechanism as Pipeline 1 — uses the SharePoint Client to get the raw HTML.

3. **Process ALL diagrams** (not just the first two). Unlike the pattern pipeline, HA/DR pages often have many diagrams (one per DR strategy per lifecycle phase). For each image:
   - Download it from SharePoint.
   - Send it to **Gemini 1.5 Flash** with an HA/DR-specific prompt: *"Analyse this HA/DR architecture diagram. Describe the infrastructure components, their redundancy setup, replication flows, and failover mechanisms."*
   - Upload the original image to GCS under `services/{service_name}/hadr-diagrams/diagram_{n}.png`.
   - Replace the `<img>` tag in the HTML with the AI-generated text description.

4. **Hierarchical chunking.** This is the key difference from Pipeline 1. Instead of sending the full HTML to Vertex Search and letting it auto-chunk, this pipeline carefully splits the content into precise pieces using a three-level hierarchy:

   - **Level 1 — DR Strategy:** The pipeline uses regex patterns to detect headings like "Backup and Restore", "Pilot Light On Demand", "Pilot Light Cold Standby", and "Warm Standby". It splits the document into four strategy sections.
   
   - **Level 2 — Lifecycle Phase:** Within each strategy section, it detects sub-headings for "Initial Provisioning", "Failover", and "Failback". Each strategy is split into three lifecycle phases.
   
   - **Level 3 — Word Window:** Each phase section is further split by a sliding window of **1500 words with 200-word overlap**. The overlap ensures that sentences at the boundary between chunks aren't cut off and lost.

   **Example:** For Amazon RDS, the pipeline might produce 17 chunks total — about 4–5 per DR strategy, each covering one lifecycle phase or part of one.

5. **Attach rich metadata to every chunk.** Each chunk gets a `struct_data` dictionary containing:
   - `service_name` (e.g., "Amazon RDS")
   - `service_type` (e.g., "Database")
   - `dr_strategy` (e.g., "Warm Standby")
   - `lifecycle_phase` (e.g., "Failover")
   - `chunk_index` (e.g., 3)
   - `diagram_gcs_urls` — a list of GCS paths to the original HA/DR diagram images that appeared in the same section as this chunk (e.g., `["gs://engen-service-hadr-images/services/Amazon_RDS/hadr-diagrams/diagram_3.png"]`)
   - `diagram_descriptions` — a list of AI-generated text descriptions of those diagrams, produced by Gemini Vision during Step 3 above (e.g., `["A Multi-AZ RDS deployment showing primary in us-east-1a with synchronous replication to standby in us-east-1b. During failover, Route 53 health checks detect failure and DNS is updated..."]`)

   **Why this matters:** At inference time, the HA/DR Retriever can issue a very precise query like *"give me all Failover chunks for Amazon RDS under the Warm Standby strategy"* using metadata filters, instead of hoping the search engine picks the right chunks on its own. The `diagram_gcs_urls` and `diagram_descriptions` fields ensure that when a chunk is retrieved, the **original reference diagrams travel with it** — so downstream generators (both the text generator and the diagram generator) can use them as **visual one-shot context** when producing new HA/DR sections and architecture diagrams for a different pattern.

   Here's what a single chunk looks like as stored in Vertex AI Search:

   ```json
   {
     "id": "Amazon_RDS_3",
     "content": "During failover, the RDS Multi-AZ instance automatically promotes the standby replica in the DR region. DNS endpoint remains the same. The promotion typically completes within 60-120 seconds...",
     "struct_data": {
       "service_name": "Amazon RDS",
       "service_description": "Managed relational database service",
       "service_type": "Database",
       "dr_strategy": "Backup and Restore",
       "lifecycle_phase": "Failover",
       "chunk_index": 3,
       "diagram_gcs_urls": ["gs://engen-service-hadr-images/services/Amazon_RDS/hadr-diagrams/diagram_3.png"],
       "diagram_descriptions": ["A Multi-AZ RDS deployment showing primary in us-east-1a with synchronous replication to standby in us-east-1b..."]
     }
   }
   ```

6. **Index each chunk.** Every chunk is uploaded as its own document to the `service-hadr-datastore` with a unique ID: `{service_name}_{chunk_index}`.

---

## Pipeline 3 — Component Catalog Pipeline (Legacy — Retired)

**What it used to do:** Scanned a GitHub repository for Terraform modules and queried AWS Service Catalog for CloudFormation products, then indexed their schemas (input variables, parameter definitions) into Vertex AI Search. This gave the code-generation agents a "catalog" to look up when generating infrastructure code.

**Source file:** `ingestion-service/pipelines/component_catalog_pipeline_legacy.py`

**Why it was retired (v2.0):** Three problems made this approach impractical:
- **Staleness** — The catalog was only as fresh as the last pipeline run. If someone added a new Terraform module to GitHub, the agents wouldn't know about it until the pipeline ran again.
- **Scope** — Only modules in pre-configured repositories were indexed. Modules in other repos were invisible.
- **Maintenance** — Running and monitoring a separate pipeline added operational overhead.

**What replaced it:** Real-time component resolution at inference time (see the companion document [REALTIME_COMPONENT_LOOKUP_WALKTHROUGH.md](REALTIME_COMPONENT_LOOKUP_WALKTHROUGH.md)). Instead of pre-indexing schemas, the agents now query GitHub and AWS Service Catalog **live, on demand** when they need a schema. This means they always get the latest version, and they can search any repository in the organization.

### How It Used to Work (For Historical Reference)

1. **Terraform Module Scanning:** Connected to a GitHub repo using PyGithub. Walked the `modules/` directory tree. For every `variables.tf` file it found, it parsed the HCL (HashiCorp Configuration Language) to extract variable names, types, defaults, and descriptions.

2. **AWS Service Catalog Scanning:** Used `boto3` (the AWS Python SDK) to call `search_products`, then for each product called `list_provisioning_artifacts` to find the latest version, then called `describe_provisioning_parameters` to extract all the input parameters and their constraints.

3. **Unified Indexing:** Both Terraform and Service Catalog schemas were normalized into a common JSON format and batch-imported into a dedicated "Component Catalog" Vertex AI Search data store.

---

## The SharePoint Client — Shared Infrastructure

All pipelines use the same **SharePoint Client** (`ingestion-service/clients/sharepoint.py`) for fetching data from Microsoft 365. Here's how it works:

### Authentication
- Uses **MSAL** (Microsoft Authentication Library) with the **Client Credentials Flow** — the pipeline logs in as the *application itself* (not as a user) using a Client ID and Client Secret registered in Azure AD.
- Tokens are valid for about 1 hour. The client automatically refreshes them **5 minutes before expiry** so long-running batch jobs never experience authentication failures.

### Key Methods
- **`fetch_pattern_list()`** — Calls the Microsoft Graph API to read all items from a SharePoint List. Handles pagination automatically (SharePoint returns about 20 items per page, so it keeps following `@odata.nextLink` until all items are fetched). Maps SharePoint's nested `fields` structure to a clean Python dictionary.
- **`fetch_page_html(page_url)`** — Given a SharePoint page URL, extracts the filename, queries the SitePages library for the matching file, and reads the `CanvasContent1` hidden field (which contains the actual HTML body of the page).
- **`download_image(image_source_url)`** — Downloads binary image data from a SharePoint drive path using the Graph API's `/content` stream endpoint.

### Resilience
- Every HTTP request goes through `_get_with_retry()` which implements:
  - **3 retries** by default
  - **Exponential backoff** (2s, 4s, 8s) for 503 errors
  - **Retry-After header respect** for 429 (rate limiting) errors
  - **30-second timeout** per request

---

## Summary: Which Pipeline Does What?

| Pipeline | Status | Source | Destination | Purpose |
|----------|--------|--------|-------------|---------|
| Vertex Search Pipeline | **Active** | SharePoint pages (patterns) | Vertex AI Search (pattern data store) | Feed the Retrieval Agent (donor pattern lookup) |
| Service HA/DR Pipeline | **Active** | SharePoint pages (per-service HA/DR docs) | Vertex AI Search (HA/DR data store) | Feed the HA/DR Retriever (disaster recovery knowledge) |
| Component Catalog Pipeline | **Retired** | GitHub repos + AWS Service Catalog | Vertex AI Search (catalog data store) | Was: Feed the Component Spec Agent — Now: replaced by real-time lookups |
