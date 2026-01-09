from vertexai.generative_models import GenerativeModel
from google.cloud import discoveryengine_v1 as discoveryengine
import json
from bs4 import BeautifulSoup
import logging
import time
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StreamAProcessor:
    """
    Stream A: Semantic Search (Vertex AI Discovery Engine)
    
    SYSTEM DESIGN: High-Level Concepts (Semantic Search)
    ----------------------------------------------------
    Goal: Enable "Concept Matching". 
    If a user searches for "scalable user management", we want to return this pattern,
    even if the words "scalable" or "user management" don't appear verbatim in the text.
    
    How:
    1. We extract raw text from HTML.
    2. We use an LLM (Gemini 1.5 Pro) to summarize it into a density-optimized abstract.
    3. We ingest this abstract into Vertex AI Discovery Engine (Stream A).
       Discovery Engine handles the embedding generation and semantic indexing automatically.
    """
    
    def __init__(self, config):
        self.config = config
        self.llm = GenerativeModel("gemini-1.5-pro")
        self.client = discoveryengine.DocumentServiceClient()
        self.parent = f"projects/{config.PROJECT_ID}/locations/global/collections/default_collection/dataStores/{config.SEARCH_DATA_STORE_ID}/branches/default_branch"

    async def prepare(self, metadata: Dict[str, Any], html_content: str, staging_dir: Path) -> Dict[str, Any]:
        """
        Phase 1: Prepare semantic document.
        
        SYSTEM DESIGN NOTE: LLM Enrichment
        We don't just dump raw HTML into the search engine. HTML is noisy (<div>, <span>).
        We use an LLM here as a "data cleaner" and "synthesizer" to create a standard
        summary format (Problem, Solution, Trade-offs) that indexes much better than raw text.
        
        This method cleans HTML, generates an LLM summary, formats the Discovery Engine document object,
        and saves it to staging. NO calls to Discovery Engine API happen here.
        
        Args:
            metadata: Properties from the SharePoint list (used for filtering tags)
            html_content: Raw HTML page content
            staging_dir: Local temproary directory
            
        Returns:
            Dict containing the prepared document ID and data payload
        """
        try:
            # Validate inputs
            if not html_content or len(html_content) < 100:
                raise ValueError("Insufficient HTML content for processing")
            
            # 1. Clean HTML
            # Beautiful Soup parses the DOM tree and gives us human-readable text.
            soup = BeautifulSoup(html_content, 'html.parser')
            text_dossier = soup.get_text(separator="\n")[:30000]
            
            if not text_dossier.strip():
                raise ValueError("No text content extracted from HTML")
            
            logger.info(f"[Stream A] Extracted {len(text_dossier)} characters of text")
            
            # 2. Summarize using LLM with retry
            prompt = f"""
            Summarize this architecture pattern into a dense technical abstract (300 words).
            Include: Core Problem, Solution Logic, Key Technologies, and Trade-offs.
            TEXT: {text_dossier}
            """
            
            summary = await self._generate_summary_with_retry(prompt)
            
            if not summary or len(summary) < 50:
                raise ValueError("Generated summary is too short or empty")
            
            logger.info(f"[Stream A] Generated summary: {len(summary)} characters")
            
            # 3. Prepare Document (but don't ingest yet)
            doc_id = f"desc_{metadata['id']}"
            doc_data = {
                "title": metadata['title'],
                "content": summary,
                "maturity": metadata.get('maturity', 'unknown'),
                "frequency": metadata.get('frequency', 0),
                "url": metadata.get('page_url', ''),
                "type": "pattern_summary",
                "pattern_id": metadata['id']
            }
            
            # Save to staging for commit phase
            # Why save to disk? Because in 2PC, if Stream B fails, we need to know 
            # exactly what we *would* have committed so we can inspect it for debugging.
            staging_file = staging_dir / "stream_a_doc.json"
            with open(staging_file, 'w') as f:
                json.dump({
                    'doc_id': doc_id,
                    'doc_data': doc_data
                }, f, indent=2)
            
            logger.info(f"[Stream A] Prepared document {doc_id} in staging")
            
            return {
                'doc_id': doc_id,
                'doc_data': doc_data,
                'staging_file': str(staging_file),
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"[Stream A] Preparation failed: {e}", exc_info=True)
            raise

    async def _generate_summary_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Generate summary with retry logic for transient failures (truly async)"""
        import asyncio
        
        for attempt in range(max_retries):
            try:
                # Use async version to avoid blocking the event loop
                response = await asyncio.to_thread(self.llm.generate_content, prompt)
                summary = response.text
                
                if summary and len(summary) > 50:
                    return summary
                
                logger.warning(f"[Stream A] Summary too short on attempt {attempt + 1}")
                
            except Exception as e:
                logger.warning(f"[Stream A] LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Async exponential backoff
        
        raise Exception("Failed to generate valid summary after retries")

    async def commit(self, prepared_data: Dict[str, Any]) -> None:
        """
        Phase 2: Commit prepared document to Vertex AI Discovery Engine.
        
        SYSTEM DESIGN NOTE: Incremental Updates
        Discovery Engine supports 'reconciliation_mode=INCREMENTAL'.
        This means if the document already exists, we update it. If not, we create it.
        This provides idempotency: running this function twice has the same effect as running it once.
        """
        try:
            doc_id = prepared_data['doc_id']
            doc_data = prepared_data['doc_data']
            
            logger.info(f"[Stream A] Committing document {doc_id} to Vertex AI...")
            
            # Create Discovery Engine document
            doc = discoveryengine.Document(
                id=doc_id,
                json_data=json.dumps(doc_data)
            )
            
            # Import to Discovery Engine
            req = discoveryengine.ImportDocumentsRequest(
                parent=self.parent,
                inline_source=discoveryengine.ImportDocumentsRequest.InlineSource(documents=[doc]),
                reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
            )
            
            operation = self.client.import_documents(request=req)
            operation.result(timeout=120)  # 2 minute timeout
            
            logger.info(f"[Stream A] ✓ Document {doc_id} committed successfully")
            
        except Exception as e:
            logger.error(f"[Stream A] Commit failed: {e}", exc_info=True)
            raise

    async def rollback(self, prepared_data: Dict[str, Any]) -> None:
        """
        Rollback: Delete document from Vertex AI Discovery Engine
        """
        try:
            doc_id = prepared_data['doc_id']
            logger.warning(f"[Stream A] Rolling back document {doc_id}...")
            
            # Delete document from Discovery Engine
            doc_name = f"{self.parent}/documents/{doc_id}"
            
            try:
                self.client.delete_document(name=doc_name)
                logger.info(f"[Stream A] ✓ Document {doc_id} deleted (rolled back)")
            except Exception as e:
                # Document might not exist if commit never happened
                logger.warning(f"[Stream A] Could not delete document (may not exist): {e}")
                
        except Exception as e:
            logger.error(f"[Stream A] Rollback failed: {e}", exc_info=True)
            # Don't raise - best effort rollback