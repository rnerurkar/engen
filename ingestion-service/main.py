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
            continue
        
        # Synchronized validation: Check content hash
        content_hash = hashlib.sha256(html_content.encode()).hexdigest()[:16]
        stored_hash = pat.get('content_hash')
        if stored_hash and stored_hash != content_hash:
            logger.warning(f"  ⚠ Content changed for {pattern_id} (hash mismatch)")
            # Continue anyway but log the drift
        
        # Add hash to metadata for storage
        pat['content_hash'] = content_hash

        # 3. Atomic Transaction Processing
        transaction = IngestionTransaction(
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