import os
import logging
import google.cloud.logging
from app import MSGraphClient, ContentProcessor, SemanticChunker, VertexIngestor
# Setup Cloud Logging
client = google.cloud.logging.Client()
client.setup_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration (Env Vars provided by Cloud Run/Secret Manager)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "global")
DATA_STORE_ID = os.environ.get("DATA_STORE_ID")
SP_SITE_ID = os.environ.get("SP_SITE_ID")
SP_LIST_ID = os.environ.get("SP_LIST_ID")

def run_etl_pipeline():
    logger.info("=== Starting Master-Detail ETL Pipeline ===")
    
    try:
        # 1. Initialize Components
        sp_client = MSGraphClient()
        processor = ContentProcessor(GCP_PROJECT_ID, GCP_LOCATION, sp_client)
        chunker = SemanticChunker()
        ingestor = VertexIngestor(GCP_PROJECT_ID, GCP_LOCATION, DATA_STORE_ID)

        # 2. Extraction (Master List)
        list_items = sp_client.fetch_list_items(SP_SITE_ID, SP_LIST_ID)
        
        total_chunks_to_ingest = []

        # 3. Processing Loop (Detail Pages)
        for item in list_items:
            fields = item.get('fields', {})
            doc_url = fields.get('PatternDocumentationURL')
            lifecycle_state = fields.get('LifecycleState')

            # Triage: Skip deprecated items
            if lifecycle_state == 'Deprecated' or not doc_url:
                logger.info(f"Skipping item: {fields.get('PatternName')} (State: {lifecycle_state})")
                continue

            logger.info(f"Processing Pattern: {fields.get('PatternName')}")
            try:
                # Fetch & Process HTML (Multimodal Gemini)
                html_content = sp_client.fetch_page_content(doc_url)
                # Determine base URL for relative images - simplified for example
                base_url = "/".join(doc_url.split("/")[:-1]) 
                markdown_text = processor.process_html_to_markdown(html_content, base_url)

                # Chunk & Join Metadata
                item_chunks = chunker.chunk_and_join(markdown_text, fields)
                total_chunks_to_ingest.extend(item_chunks)
                
            except Exception as e:
                # Log error but continue processing other items
                logger.error(f"Failed to process pattern {fields.get('PatternName')}: {e}", exc_info=True)

        # 4. Ingestion (Batch Push)
        if total_chunks_to_ingest:
            logger.info(f"Beginning batch ingestion of {len(total_chunks_to_ingest)} total chunks.")
            ingestor.ingest_chunks(total_chunks_to_ingest)
        else:
            logger.warning("No valid chunks generated. Skipping ingestion.")

        logger.info("=== ETL Pipeline Completed Successfully ===")

    except Exception as e:
        logger.critical(f"ETL Pipeline Failed Critical: {e}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    run_etl_pipeline()