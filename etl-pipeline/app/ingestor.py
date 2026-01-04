import logging
from typing import List, Dict, Any
from google.cloud import discoveryengine_v1 as discoveryengine

logger = logging.getLogger(__name__)

class VertexIngestor:
    def __init__(self, project_id: str, location: str, data_store_id: str):
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id
        self.client = discoveryengine.DocumentServiceClient()
        self.parent = self.client.branch_path(
            project=self.project_id,
            location=self.location,
            data_store=self.data_store_id,
            branch="default_branch"
        )
        logger.info(f"Vertex AI Ingestor initialized for Data Store: {data_store_id}")

    def ingest_chunks(self, chunks: List[Dict[str, Any]]):
        """Batches and pushes chunks to Vertex AI Search using Inline JSON."""
        if not chunks:
            logger.warning("No chunks provided for ingestion.")
            return

        # Convert dicts to Discovery Engine Document objects
        documents = [
            discoveryengine.Document(
                id=chunk['id'],
                json_data=chunk['jsonData']
            ) for chunk in chunks
        ]

        # Define request message with inline documents
        request = discoveryengine.ImportDocumentsRequest(
            parent=self.parent,
            inline_source=discoveryengine.InlineSource(documents=documents),
            # UPSERT mode ensures existing documents with same ID are updated
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.UPSERT,
        )

        logger.info(f"Starting import of {len(documents)} chunks to Vertex AI...")
        try:
            # Make the request and wait for the Long Running Operation (LRO)
            operation = self.client.import_documents(request=request)
            logger.info(f"Waiting for import operation completion (LRO: {operation.operation.name})...")
            response = operation.result(timeout=900) # 15 minute timeout for batch
            
            logger.info(f"Import completed successfully. Status: {response}")

            # Check for failures within a generally successful batch
            if response.error_samples:
                 logger.error(f"Encountered {len(response.error_samples)} errors during import samples: {response.error_samples}")

        except Exception as e:
            logger.error(f"Fatal error during Vertex AI import: {e}")
            raise