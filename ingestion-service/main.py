import asyncio
import logging
import tempfile
import hashlib
from pathlib import Path
from config import Config
from clients.sharepoint import SharePointClient
from processors.semantic import StreamAProcessor
from processors.visual import StreamBProcessor
from processors.content import StreamCProcessor
from transaction_manager import TransactionCoordinator, IngestionTransaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_ingestion():
    cfg = Config()
    
    # Initialize Clients
    sp_client = SharePointClient(cfg)
    proc_a = StreamAProcessor(cfg)
    proc_b = StreamBProcessor(cfg, sp_client)
    proc_c = StreamCProcessor(cfg)
    
    # Initialize Transaction Coordinator with platform-appropriate staging
    staging_root = Path(tempfile.gettempdir()) / "engen_staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using staging directory: {staging_root}")
    
    checkpoint_dir = Path(tempfile.gettempdir()) / "engen_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    coordinator = TransactionCoordinator(str(checkpoint_dir))

    # 1. Fetch Catalog
    logger.info("Fetching Pattern Catalog...")
    patterns = sp_client.fetch_pattern_list()
    
    total_patterns = len(patterns)
    success_count = 0
    skip_count = 0
    failure_count = 0
    
    logger.info(f"Found {total_patterns} patterns to process")
    
    for idx, pat in enumerate(patterns, 1):
        pattern_id = pat['id']
        pattern_title = pat['title']
        
        logger.info(f"[{idx}/{total_patterns}] Processing Pattern: {pattern_title} ({pattern_id})")
        
        # Check if already completed
        if coordinator.is_completed(pattern_id):
            logger.info(f"  ✓ Pattern {pattern_id} already completed (skipping)")
            skip_count += 1
            continue
        
        # 2. Fetch Page Content (HTML)
        if not pat.get('page_url'):
            logger.warning(f"  ⚠ Pattern {pattern_id} has no page_url (skipping)")
            skip_count += 1
            continue
        
        try:
            html_content = sp_client.fetch_page_html(pat['page_url'])
            if not html_content:
                logger.warning(f"  ⚠ No HTML content for {pattern_id} (skipping)")
                skip_count += 1
                continue
        except Exception as e:
            logger.error(f"  ✗ Failed to fetch HTML for {pattern_id}: {e}")
            failure_count += 1
            # 0. Pre-flight environment checks (critical)
            await verify_environment(cfg)

            # 1. Fetch Catalog
        
        # Synchronized validation: Check content hash
        content_hash = hashlib.sha256(html_content.encode()).hexdigest()[:16]
        stored_hash = pat.get('content_hash')
        if stored_hash and stored_hash != content_hash:
            logger.warning(f"  ⚠ Content changed for {pattern_id} (hash mismatch)")
            # Continue anyway but log the drift
        
        # Add hash to metadata for storage
        pat['content_hash'] = content_hash
            # Bounded concurrency across patterns (high priority)
            concurrency = int(os.getenv("INGEST_CONCURRENCY", "4"))
            sem = asyncio.Semaphore(concurrency)

            async def process_pattern(idx: int, pat: dict):
                async with sem:
                    pattern_id = pat['id']
                    pattern_title = pat['title']
                    logger.info(f"[{idx}/{total_patterns}] Processing Pattern: {pattern_title} ({pattern_id})")
                    if coordinator.is_completed(pattern_id):
                        logger.info(f"  ✓ Pattern {pattern_id} already completed (skipping)")
                        return 'skip'
                    if not pat.get('page_url'):
                        logger.warning(f"  ⚠ Pattern {pattern_id} has no page_url (skipping)")
                        return 'skip'
                    try:
                        html_content = sp_client.fetch_page_html(pat['page_url'])
                        if not html_content:
                            logger.warning(f"  ⚠ No HTML content for {pattern_id} (skipping)")
                            return 'skip'
                    except Exception as e:
                        logger.error(f"  ✗ Failed to fetch HTML for {pattern_id}: {e}")
                        return 'fail'
                    content_hash = hashlib.sha256(html_content.encode()).hexdigest()[:16]
                    stored_hash = pat.get('content_hash')
                    if stored_hash and stored_hash != content_hash:
                        logger.warning(f"  ⚠ Content changed for {pattern_id} (hash mismatch)")
                    pat['content_hash'] = content_hash
                    transaction = IngestionTransaction(pattern_id=pattern_id, pattern_title=pattern_title, staging_base=str(staging_root))
                    processors = {'A': proc_a, 'B': proc_b, 'C': proc_c}
                    try:
                        success = await coordinator.execute_transaction(transaction=transaction, processors=processors, metadata=pat, html_content=html_content)
                        if success:
                            logger.info(f"  ✓ Successfully ingested {pattern_title}")
                            return 'success'
                        else:
                            logger.error(f"  ✗ Transaction failed for {pattern_title}")
                            return 'fail'
                    except Exception as e:
                        logger.error(f"  ✗ Failed to process {pattern_title}: {e}", exc_info=True)
                        return 'fail'

            tasks = [process_pattern(idx, pat) for idx, pat in enumerate(patterns, 1)]
            results = await asyncio.gather(*tasks)

            for res in results:
                if res == 'success':
                    success_count += 1
                elif res == 'skip':
                    skip_count += 1
                else:
                    failure_count += 1

        # 3. Atomic Transaction Processing
        transaction = IngestionTransaction(

        async def verify_environment(cfg: Config):
            """Pre-flight checks for critical dependencies with short timeouts."""
            import asyncio
            import socket
            from google.cloud import storage, firestore
            from google.cloud import discoveryengine_v1 as discoveryengine
            from google.cloud import aiplatform
    
            logger.info("Running pre-flight environment checks...")
            # GCS bucket access
            try:
                storage_client = storage.Client(project=cfg.PROJECT_ID)
                bucket = storage_client.bucket(cfg.GCS_BUCKET)
                _ = bucket.exists()
                logger.info("✓ GCS bucket reachable")
            except Exception as e:
                raise RuntimeError(f"GCS bucket check failed: {e}")
            # Firestore availability
            try:
                db = firestore.Client(project=cfg.PROJECT_ID)
                _ = db.collection(cfg.FIRESTORE_COLLECTION).document("_probe").get()
                logger.info("✓ Firestore reachable")
            except Exception as e:
                raise RuntimeError(f"Firestore check failed: {e}")
            # Discovery Engine document import endpoint
            try:
                client = discoveryengine.DocumentServiceClient()
                parent = f"projects/{cfg.PROJECT_ID}/locations/global/collections/default_collection/dataStores/{cfg.SEARCH_DATA_STORE_ID}/branches/default_branch"
                # lightweight call: get document that won't exist to validate endpoint
                try:
                    client.get_document(name=f"{parent}/documents/__probe__")
                except Exception:
                    pass
                logger.info("✓ Discovery Engine reachable")
            except Exception as e:
                raise RuntimeError(f"Discovery Engine check failed: {e}")
            # Vector Search endpoint
            try:
                aiplatform.init(project=cfg.PROJECT_ID, location=cfg.LOCATION)
                _ = aiplatform.MatchingEngineIndexEndpoint(cfg.VECTOR_INDEX_ENDPOINT)
                logger.info("✓ Vector Search endpoint reachable")
            except Exception as e:
                raise RuntimeError(f"Vector Search check failed: {e}")
            pattern_id=pattern_id,
            pattern_title=pattern_title,
            staging_base=str(staging_root)
        )
        
        # Prepare processor dictionary with correct keys
        processors = {
            'A': proc_a,  # Stream A - Semantic
            'B': proc_b,  # Stream B - Visual
            'C': proc_c   # Stream C - Content
        }
        
        try:
            # Execute atomic transaction using coordinator
            success = await coordinator.execute_transaction(
                transaction=transaction,
                processors=processors,
                metadata=pat,
                html_content=html_content
            )
            
            if success:
                success_count += 1
                logger.info(f"  ✓ Successfully ingested {pattern_title}")
            else:
                failure_count += 1
                logger.error(f"  ✗ Transaction failed for {pattern_title}")
            
        except Exception as e:
            logger.error(f"  ✗ Failed to process {pattern_title}: {e}", exc_info=True)
            failure_count += 1
    
    # Final Summary
    logger.info("=" * 60)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Patterns:    {total_patterns}")
    logger.info(f"Successfully Ingested: {success_count}")
    logger.info(f"Skipped:          {skip_count}")
    logger.info(f"Failed:           {failure_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_ingestion())