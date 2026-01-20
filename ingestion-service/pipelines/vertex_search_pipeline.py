"""
Vertex AI Search Ingestion Pipeline
-----------------------------------
This module handles the end-to-end processing of SharePoint patterns into Vertex AI Search.
It consolidates Stream A (Metadata), Stream B (Diagrams/Images), and Stream C (Text) 
into a single managed ingestion process.

Key Features:
1. Multimodal Extraction: Uses Gemini Pro Vision to generate text descriptions for diagrams.
2. Content Enrichment: Injects diagram descriptions directly into the HTML context.
3. Media Handling: Offloads images to GCS and rewrites HTML references.
4. Managed Indexing: Pushes final content + metadata to Google Cloud Discovery Engine.
"""

import logging
import base64
import os
import sys
from typing import Dict, List, Any, Tuple
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Google Cloud Imports
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Image

logger = logging.getLogger(__name__)

class VertexSearchPipeline:
    def __init__(
        self, 
        sp_client, 
        project_id: str, 
        location: str, 
        data_store_id: str, 
        gcs_bucket_name: str
    ):
        """
        Args:
            sp_client: Instance of SharePointClient.
            project_id: GCP Project ID.
            location: Vertex AI location (e.g., 'global' or 'us-central1').
            data_store_id: The Vertex AI Search Data Store ID.
            gcs_bucket_name: Name of the bucket to store images.
        """
        self.sp_client = sp_client
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id
        
        # Initialize GCP Clients
        self.storage_client = storage.Client(project=project_id)
        self.bucket = self.storage_client.bucket(gcs_bucket_name)
        self.doc_client = discoveryengine.DocumentServiceClient()
        
        # Initialize Vertex AI (LLM)
        # LLM usually requires regional endpoint (e.g. us-central1) unlike global search
        vertexai.init(project=project_id, location="us-central1") 
        self.vision_model = GenerativeModel("gemini-1.5-flash") # Efficient multimodal model

    def run_ingestion(self):
        """Main entry point to run the batch ingestion."""
        logger.info("Starting Vertex AI Search ingestion...")
        
        # 1. Fetch all patterns from SharePoint List
        patterns = self.sp_client.fetch_pattern_list()
        
        for pattern in patterns:
            try:
                self.process_single_pattern(pattern)
            except Exception as e:
                logger.error(f"Failed to process pattern {pattern['id']}: {e}", exc_info=True)

    def process_single_pattern(self, pattern_meta: Dict[str, Any]):
        """
        Orchestrates the transformation for a single pattern.
        
        SYSTEM DESIGN NOTE: Consolidation of Streams
        --------------------------------------------
        This method replaces the previous multi-stream architecture:
        - Stream A (Metadata): Now mapped directly to Vertex Search 'struct_data'.
        - Stream B (Diagrams): Now processed via 'gemini-1.5-flash' and descriptions injected into HTML.
        - Stream C (Text): Content is now kept as HTML (no manual chunking) and sent to Vertex.
        """
        logger.info(f"Processing pattern: {pattern_meta['title']} ({pattern_meta['id']})")
        
        # 1. Fetch raw HTML content
        # We fetch the full page content from SharePoint to serve as our base knowledge source.
        raw_html = self.sp_client.fetch_page_html(pattern_meta['page_url'])
        if not raw_html:
            logger.warning(f"No HTML content found for {pattern_meta['title']}")
            return

        # 2. Extract Images, Store in GCS, Generate Descriptions
        # Returns: Modified HTML (with new GCS Links) and the generated descriptions
        # CRITICAL: This step turns visual data (diagrams) into text (descriptions) so RAG can retrieve it.
        updated_html, image_descriptions = self._process_images(raw_html, pattern_meta['id'])
        
        # 3. Enrich HTML with Descriptions
        # We inject the LLM-generated descriptions back into the HTML so the search engine indexes them together.
        final_html = self._enrich_html_content(updated_html, image_descriptions)
        
        # 4. Map Metadata & Push to Vertex AI Search
        self._index_document(pattern_meta, final_html)

    def _process_images(self, html_content: str, pattern_id: str) -> Tuple[str, List[str]]:
        """
        Parses HTML, finds first 2 images, uploads to GCS, interprets with LLM, 
        and updates HTML src attributes.

        Why only first 2 images?
        - In our SharePoint pattern template, Image 1 is the 'Component Diagram' and Image 2 is the 'Sequence Diagram'.
        - Processing all images would be costly and less relevant.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        images = soup.find_all('img')
        descriptions = []
        
        # Limit to first 2 images (Component & Sequence diagrams typically)
        target_images = images[:2]
        
        for idx, img_tag in enumerate(target_images):
            original_src = img_tag.get('src')
            if not original_src:
                continue

            logger.info(f"Processing image {idx+1}/2 for pattern {pattern_id}...")

            # A. Download from SharePoint
            try:
                image_data = self.sp_client.download_image(original_src)
                if not image_data:
                    logger.warning(f"Empty image data for {original_src}")
                    continue
            except Exception as e:
                logger.warning(f"Failed to download image {original_src}: {e}")
                continue

            # B. Generate Description using Gemini
            try:
                description = self._generate_image_description(image_data)
                descriptions.append(f"Diagram {idx+1} Description: {description}")
            except Exception as e:
                logger.warning(f"LLM description failed: {e}")
                descriptions.append("Diagram Description: [Analysis Failed]")

            # C. Upload to GCS
            try:
                blob_name = f"patterns/{pattern_id}/images/diag_{idx}.png"
                gcs_url = self._upload_to_gcs(image_data, blob_name)

                # D. Replace src in HTML
                img_tag['src'] = gcs_url
                # Add alt text for accessibility/searchability
                img_tag['alt'] = description if description else "Pattern Diagram"
            except Exception as e:
                 logger.warning(f"Failed to upload image or update HTML: {e}")

        return str(soup), descriptions

    def _generate_image_description(self, image_bytes: bytes) -> str:
        """
        Calls Gemini 1.5 Flash to describe the technical diagram.
        """
        prompt = """
        Analyze this technical architecture diagram. 
        Provide a detailed textual description of the components, relationships, and flow depicted.
        Focus on technical accuracy as this is for a RAG knowledge base.
        """
        
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        
        response = self.vision_model.generate_content(
            [prompt, image_part],
            generation_config={"max_output_tokens": 512, "temperature": 0.2}
        )
        return response.text

    def _upload_to_gcs(self, image_data: bytes, blob_name: str) -> str:
        """
        Uploads bytes to GCS and returns the public URL.
        """
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(image_data, content_type="image/png")
        
        # Construct path (assuming bucket is either public or accessible via signed URL logic)
        # Using standard storage.googleapis.com format
        return f"https://storage.googleapis.com/{self.bucket.name}/{blob_name}"

    def _enrich_html_content(self, html_content: str, descriptions: List[str]) -> str:
        """
        Injects the generated descriptions as the first section of the HTML.
        """
        if not descriptions:
            return html_content

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Create a new div container for our AI-generated context
        ai_context_div = soup.new_tag("div", attrs={"class": "ai-generated-context", "style": "background-color: #f0f0f0; padding: 15px; margin-bottom: 20px;"})
        
        header = soup.new_tag("h2")
        header.string = "AI Generated Diagram Descriptions"
        ai_context_div.append(header)
        
        for desc in descriptions:
            p = soup.new_tag("p")
            p.string = desc
            ai_context_div.append(p)
            
        # Prepend to body or beginning of parsed fragment
        if soup.body:
            soup.body.insert(0, ai_context_div)
        else:
            soup.insert(0, ai_context_div)
            
        return str(soup)

    def _index_document(self, metadata: Dict[str, Any], html_content: str):
        """
        Pushes the structured data and content to Vertex AI Search.
        
        SYSTEM DESIGN NOTE: Vertex AI Search Data Model
        -----------------------------------------------
        We use the 'Unstructured Data with Metadata' model.
        - 'content': The enriched HTML blob. The engine will handle chunking, embedding, and indexing of this text.
        - 'struct_data': Key-value pairs used strictly for filtering (e.g., "Maturity: Production").
        
        Unlike Vector Search, we do NOT manage embeddings manually here.
        """
        parent = self.doc_client.branch_path(
            project=self.project_id,
            location=self.location,
            data_store=self.data_store_id,
            branch="default_branch",
        )

        # 1. Structure the Metadata (Stream A)
        # Vertex Search matches these keys against the schema defined in the Data Store
        struct_data = {
            "title": metadata.get("title"),
            "owner": metadata.get("owner"),
            "maturity": metadata.get("maturity"),
            "status": metadata.get("status"),
            "frequency": metadata.get("frequency"),
            "category": metadata.get("category"),
            "original_url": metadata.get("page_url"),
            "last_updated": metadata.get("last_updated", "")
        }

        # 2. Create the Document Object
        # Note: We provide both 'struct_data' (for filtering) and 'content' (for vectorization/RAG)
        document = discoveryengine.Document(
            id=metadata["id"],
            struct_data=struct_data,
            content=discoveryengine.Document.Content(
                mime_type="text/html",
                raw_bytes=html_content.encode("utf-8")
            )
        )

        # 3. Write Document (Update/Upsert)
        request = discoveryengine.WriteDocumentRequest(
            parent=parent,
            document=document
        )

        self.doc_client.write_document(request=request)
        logger.info(f"Successfully indexed document: {metadata['id']}")

if __name__ == "__main__":
    # 0. Load Environment Variables from .env file
    load_dotenv()
    
    # 1. Setup Python Path to include 'ingestion-service' root
    # This ensures we can import 'config' and 'clients' modules
    current_file_path = os.path.abspath(__file__)
    pipeline_dir = os.path.dirname(current_file_path)   # .../pipelines
    service_root = os.path.dirname(pipeline_dir)        # .../ingestion-service
    
    if service_root not in sys.path:
        sys.path.append(service_root)

    # 2. Local Imports (now resolvable)
    from config import Config
    from clients.sharepoint import SharePointClient

    # 3. Configure Logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        logger.info("Initializing Vertex Search Pipeline...")
        
        # 4. Initialize Configuration & Clients
        config = Config()
        
        # Validate critical inputs
        if not all([config.PROJECT_ID, config.GCS_BUCKET, config.SEARCH_DATA_STORE_ID]):
             logger.error("Missing required Env variables: GCP_PROJECT_ID, GCS_IMAGE_BUCKET, or VERTEX_SEARCH_DS_ID")
             sys.exit(1)

        sp_client = SharePointClient(config)
        
        # 5. Instantiate Pipeline
        pipeline = VertexSearchPipeline(
            sp_client=sp_client,
            project_id=config.PROJECT_ID,
            location=config.LOCATION,
            data_store_id=config.SEARCH_DATA_STORE_ID,
            gcs_bucket_name=config.GCS_BUCKET
        )
        
        # 6. Run
        pipeline.run_ingestion()
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
