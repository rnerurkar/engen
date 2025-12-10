import asyncio
import logging
from config import Config
from clients.sharepoint import SharePointClient
from processors.semantic import StreamAProcessor
from processors.visual import StreamBProcessor
from processors.content import StreamCProcessor

logging.basicConfig(level=logging.INFO)

async def run_ingestion():
    cfg = Config()
    
    # Initialize Clients
    sp_client = SharePointClient(cfg)
    proc_a = StreamAProcessor(cfg)
    proc_b = StreamBProcessor(cfg, sp_client)
    proc_c = StreamCProcessor(cfg)

    # 1. Fetch Catalog
    logging.info("Fetching Pattern Catalog...")
    patterns = sp_client.fetch_pattern_list()
    
    for pat in patterns:
        logging.info(f"Processing Pattern: {pat['title']} ({pat['id']})")
        
        # 2. Fetch Page Content (HTML)
        # Note: If page_url is missing, skip
        if not pat.get('page_url'): continue
        
        html_content = sp_client.fetch_page_html(pat['page_url'])
        if not html_content: continue

        # 3. Synchronized Stream Processing
        # We run these in sequence here for reliability, but asyncio.gather can be used for speed
        try:
            # Stream A: Semantic (Vertex Search)
            proc_a.process(pat, html_content)
            
            # Stream B: Visual (Vector Search + GCS)
            proc_b.process(pat, html_content, sp_client) # Pass client for downloads
            
            # Stream C: Content (Firestore)
            proc_c.process(pat, html_content)
            
            logging.info(f"Successfully ingested {pat['title']}")
            
        except Exception as e:
            logging.error(f"Failed to process {pat['title']}: {e}")

if __name__ == "__main__":
    asyncio.run(run_ingestion())