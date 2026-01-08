# Ingestion Architecture Comparison: Managed SP Connector vs. Custom Ingestion Service

**Analysis Date:** January 8, 2026
**Context:** Comparative analysis between the "Enterprise Knowledge Intelligence Framework - SharePoint Version 2.1" design and the `ingestion-service` codebase.

---

## Executive Summary

*   **Managed Connector (Design Doc 2.1):** Best for **Enterprise Compliance & Text Search**. It excels at handling ACLs (Access Control Lists) and requires minimal code maintenance, but relies on complex Agentic reasoning at runtime to join data or analyze images.
*   **Custom Ingestion Service (Codebase):** Best for **Advanced RAG & Multimodal Intelligence**. It excels at "Visual Search" (finding similar diagrams), precise content atomization (Firestore), and pre-computation (LLM summarization during ingestion), but requires maintaining a complex Python codebase.

---

## Detailed Comparison Matrix

| Feature | Design A: Managed Connector (<br>`Framework v2.1.md`) | Design B: Custom Ingestion Service<br>([`ingestion-service`](ingestion-service/)) |
| :--- | :--- | :--- |
| **Ingestion Type** | **Pull:** Google crawls SharePoint via Graph API. | **Push:** Python scripts extract, process, and push data. |
| **Master-Detail Handling** | **Agentic Join (Inference Time):**<br>The List and Page are indexed separately. The Agent must query the List, get a URL, then query the Page (see *Section 4.1* in Framework doc). | **Pre-joined Enrichment (Ingestion Time):**<br>Metadata from the Master List is injected into the Page content *before* storage (see [`StreamAProcessor`](ingestion-service/processors/semantic.py) logic). No extra Agent steps needed. |
| **Visual Capabilities** | **Text Extraction (OCR):**<br>Uses Document AI to extract text/tables from images. The Agent must *re-fetch* raw image bytes at runtime for Gemini to "see" the chart (*Section 3.1*). | **Vector Embeddings (Premade):**<br>[`StreamBProcessor`](ingestion-service/processors/visual.py) generates embeddings using mult-modal embedding models. Allows **Visual Similarity Search** (finding similar patterns by looking at a diagram). |
| **Retrieval Granularity** | **Chunk-Based:**<br>Returns chunks determined by Google's layout parser. | **Semantic & Atomized:**<br>1. **Summaries** (Discovery Engine)<br>2. **Embeddings** (Vector Search)<br>3. **Exact Sections** (Firestore keys) |
| **Security (ACLs)** | **Native Sync:**<br>Syncs Entra ID groups to Google Cloud Identity. Search results automatically respect user permissions (*Section 2.3*). | **Service-Level:**<br>Typically runs as a Service Account. ACL filtering must be implemented manually in the application logic or post-filtration. |
| **Maintenance** | **Low:** Configuration-based in Google Cloud Console. | **High:** Requires code maintenance, error handling, and infrastructure (Cloud Run). |

---

## Deep Dive Analysis

### 1. Master-Detail Relationship Strategy

*   **Managed Connector (Weakness):** As described in *Section 4.1 Use Case 1* of the Framework doc, the connector creates a disconnection. A "Pattern" item in a list and its "Documentation" page are two separate search results. The `MasterDetailTool` must run two separate search queries to synthesize an answer.
*   **Custom Service (Strength):** The [`ingestion-service`](ingestion-service/) merges this context. When [`StreamAProcessor`](ingestion-service/processors/semantic.py) processes a page, it already holds the metadata (Maturity, Frequency, Owner) from the list. The resulting object in Vertex AI Discovery Engine is a complete "Dossier" of the pattern, reducing Agent complexity and latency.

### 2. Multimodal & Visual Intelligence

*   **Managed Connector (Reactive):** The connector uses OCR to turn images into text indexing. It does not natively store image embeddings for retrieval.
    *   *Workflow:* Search finds text -> returns file path -> Agent invokes `MSGraphFetcher` -> downloads bytes -> Gemini analyzes.
    *   *Latency:* High (requires realtime download and image processing).
*   **Custom Service (Proactive):** The [`StreamBProcessor`](ingestion-service/processors/visual.py) treats images as first-class citizens.
    *   *Workflow:* It downloads images *during ingestion*, generates vector embeddings, and stores them in Vertex AI Vector Search.
    *   *Capability:* This enables **"Show me patterns with architecture diagrams looking like this"**—a feature the Connector cannot do natively.

### 3. Data Processing & Quality

*   **Managed Connector:** Relies on Document AI's Layout Parser (*Section 2.2*). It is excellent at preserving table structures (converting them to Markdown/HTML) which is often hard to do with custom BeautifulSoup scripts.
*   **Custom Service:** Uses [`StreamCProcessor`](ingestion-service/processors/content.py) to "atomize" content into Firestore. This allows for extremely precise retrieval, such as "Get the *Implementation* section of Pattern X," rather than relying on a search engine to find a relevant chunk. It also uses an LLM in [`StreamAProcessor`](ingestion-service/processors/semantic.py) to write a dense technical summary *before* indexing, improving search relevance.

---

## Recommendation

**Stick with the [`ingestion-service`](ingestion-service/) (Custom Pipeline)** if your requirements include:
1.  **Visual Similarity Search:** If users need to search *by* image or find similar diagrams.
2.  **Specific Section Retrieval:** If Agents need to pull specific sections ("Implementation", "Trade-offs") deterministically from Firestore rather than probabilistically from Search.
3.  **Low Latency RAG:** The Custom service pre-joins metadata, avoiding the double-hop search required by the "Agentic Join" pattern in the Design Doc.

**Switch to the Managed Connector** only if:
1.  **Strict ACL Compliance:** You require User-level permission trimming to work out of the box without building custom filtering logic.
2.  **Maintenance is the Bottle Neck:** If the engineering team cannot support the maintenance of the Python ETL pipeline defined in [`ingestion-service`](ingestion-service/).
