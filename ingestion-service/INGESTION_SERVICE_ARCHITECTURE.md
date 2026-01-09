# Ingestion Service: Technical Architecture Guide
**Author:** Principal Systems Engineer
**Target Audience:** Development Team

---

## 1. The Big Picture: Why this architecture?

Welcome to the `ingestion-service`. Content ingestion might sound simple ("Move data from SharePoint to Google Cloud"), but in an Agentic AI system, data quality and consistency are everything.

If we simply wrote a script that reads a page and uploads it, we would face race conditions, partial failures (e.g., text uploaded but images failed), and unmanageable error states.

To solve this, we use distinct **Design Patterns**:

1.  **Parallel Processing (The 3 Streams):** We split the data into three "modalities" (Text, Visual, Content) and process them simultaneously for speed.
2.  **Two-Phase Commit (2PC):** We never write directly to the database. We first **Prepare** (stage the data), and only if *all* streams succeed, we **Commit** (save). If any stream fails, we **Rollback** (undo).
3.  **Atomicity:** A pattern is treated as a single atomic unit. It either exists fully in our system, or it doesn't exist at all.

---

## 2. The Core Components

### 2.1 The Conductor: `main.py`
This is the entry point. Think of `main.py` as the **Project Manager**. It doesn't do the heavy lifting itself; it assigns work to others.

**Key Responsibilities:**
*   **Environment Check:** Ensures database connections and API keys are valid before starting (`verify_environment`).
*   **SharePoint Traversal:** Connects to Microsoft Graph API/SharePoint Graph to fetch the list of items.
*   **Concurrency Control:** Uses `asyncio.Semaphore` to limit how many patterns we process at once (e.g., 5 at a time) so we don't crash our memory or get rate-limited by SharePoint.
*   **The Loop:** It iterates through every SharePoint item and initiates the `TransactionManager`.

### 2.2 The Safety Net: `transaction_manager.py`
This is the most critical logic in the system. It enforces the **Two-Phase Commit** protocol.

**The Workflow:**
1.  **`prepare()`**: It asks all three processors (A, B, C) to process their data but **not** save it to the database yet. They save their results to a temporary `staging/` directory on the local disk.
2.  **`save_checkpoint()`**: It writes a file saying, "I have successfully prepared Pattern X." If the server crashes now, we know we got this far.
3.  **`commit()`**: It tells all processors: "Okay, everything looks good. Push your staged data to the real databases (Vertex AI, Firestore, etc.)."
4.  **`rollback()`**: If *any* processor fails during the Prepare or Commit phase, this method is called. It attempts to delete any partial data that might have leaked into the system.

---

## 3. The Workers: The Processors

Each processor focuses on one specific aspect of the data ("Separation of Concerns").

### 3.1 Stream A: Semantic Processor (`processors/semantic.py`)
*   **Goal:** High-level understanding. Used by the Search Engine to find relevant documents.
*   **Destination:** Vertex AI Discovery Engine (Datastore).
*   **Key Logic:**
    1.  **Extract Text:** Uses `BeautifulSoup` to strip HTML tags and get raw text.
    2.  **Summarize (LLM):** It sends the text to **Gemini 1.5 Pro** with a specific prompt: *"Summarize this architecture pattern..."*. We trust the LLM to understand the dense technical content better than a keyword search would.
    3.  **Metadata Injection:** It attaches tags like `Status`, `Owner`, and `Maturity` to the document so we can filter results later (e.g., "Show me only Approved patterns").
*   **Why Separation?** By separating this, we can tune the summarization prompt without breaking the image search.

### 3.2 Stream B: Visual Processor (`processors/visual.py`)
*   **Goal:** Visual grounding. Used to find patterns based on diagrams or charts.
*   **Destination:** Vertex AI Vector Search (Embeddings).
*   **Key Logic:**
    1.  **Image Extraction:** Finds all `<img src="...">` tags.
    2.  **Download:** Fetches the raw image bytes.
    3.  **Vectorization:** Sends the image to the **Multimodal Embedding Model**. This converts the image into a list of 768 numbers (a vector) representing its *visual meaning*.
    4.  **Indexing:** pushes these vectors to the Vector Search index.
*   **Cool Factor:** This allows the "Consulting Copilot" to answer questions like: *"Do we have any patterns that look like a Hub-and-Spoke network?"*

### 3.3 Stream C: Content Processor (`processors/content.py`)
*   **Goal:** Precision retrieval. Used by the Agent to grab exact text sections to answer specific questions.
*   **Destination:** Google Cloud Firestore (NoSQL DB).
*   **Key Logic:**
    1.  **Chunking:** It breaks the long HTML page into logical sections based on headings (`<h2>`, `<h3>`).
    2.  **Enrichment:**
        *   It injects the Pattern Metadata (Owner, Status) into *each* chunk.
        *   **Image Description:** If a chunk has an image, it asks Gemini to *describe* the image in text and replaces the `<img>` tag with that description. This allows text search to "find" the image concepts.
    3.  **Atomization:** Saves each section as a separate document in Firestore.
*   **Why Firestore?** Unlike Vector Search (which gives approximate matches), Firestore allows us to say: *"Give me exactly the 'Implementation' section of 'Pattern-123'."*

---

## 4. Code Walkthrough (Mental Model)

Imagine processing **one pattern**: "Cloud Spoke Architecture".

```python
# Simplified Logic Flow

# 1. Main Loop
pattern = sharepoint.get_next_item()

# 2. Transaction Start
t_mgr = TransactionManager()

try:
    # 3. PHASE 1: PREPARE (Staging)
    # Stream A: Writes a summary JSON to disk
    # Stream B: Downloads images, calcs vectors, saves JSON to disk
    # Stream C: Chunks text, describes images, saves JSON to disk
    await t_mgr.prepare(pattern)

    # 4. PHASE 2: COMMIT (Persistence)
    # Stream A: Uploads JSON to Discovery Engine
    # Stream B: Uploads Vectors to Vector Search
    # Stream C: Writes Documents to Firestore
    await t_mgr.commit()

except Exception:
    # 5. ROLLBACK (Cleanup)
    # Undo anything that might have been uploaded
    await t_mgr.rollback()
```

## 5. Developer Tips for this Codebase

1.  **Async/Await is Mandatory:** We perform many network calls (SharePoint, Vertex AI, Firestore). All these processes must be `async`. Never use `time.sleep()`; always use `await asyncio.sleep()`.
2.  **Idempotency:** Designing for failure means assuming the code will crash halfway through. The `rollback` and `prepare` methods should be **idempotent**—running them twice shouldn't break anything.
3.  **Type Hinting:** We use Python type hints (`Dict[str, Any]`, `List[str]`) extensively. This helps catch bugs before we run the code.
4.  **Logging:** We log heavily at the `INFO` level. In a pipeline running for hours, logs are your only window into what is happening.

---
**End of Document**
