from google.cloud import storage
from google.cloud import aiplatform
from vertexai.vision_models import MultiModalEmbeddingModel, Image
from bs4 import BeautifulSoup
import uuid
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StreamBProcessor:
    """Stream B: Visual Search (Vector Index + GCS)"""
    
    def __init__(self, config, sp_client):
        self.config = config
        self.embed_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(config.GCS_BUCKET)
        self.sp_client = sp_client
        
        # Initialize Vector Search client
        aiplatform.init(project=config.PROJECT_ID, location=config.LOCATION)
        self.index_endpoint = config.VECTOR_INDEX_ENDPOINT
        self.deployed_index_id = config.DEPLOYED_INDEX_ID

    async def prepare(self, metadata: Dict[str, Any], html_content: str, staging_dir: Path) -> Dict[str, Any]:
        """
        Phase 1: Prepare visual embeddings.
        
        This method finds <img> tags, downloads the binary data, generates 
        a vector embedding using the Multimodal model, and saves both to staging.
        
        Args:
            metadata: SharePoint item metadata
            html_content: Raw HTML content
            staging_dir: Local staging directory
            
        Returns:
            Dict containing list of image paths and their vector embeddings
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            imgs = soup.find_all('img')
            
            if not imgs:
                logger.warning(f"[Stream B] No images found in HTML")
                # Allow patterns without images
                return {'images': [], 'vectors': []}
            
            logger.info(f"[Stream B] Found {len(imgs)} images in HTML")
            
            staged_images = []
            vectors = []
            
            for idx, img in enumerate(imgs):
                src = img.get('src')
                if not src or "icon" in src.lower():
                    continue
                
                try:
                    # Download image from SharePoint
                    logger.debug(f"[Stream B] Downloading image {idx + 1}: {src}")
                    image_bytes = self.sp_client.download_image(src)
                    
                    if not image_bytes:
                        logger.warning(f"[Stream B] Failed to download image: {src}")
                        continue
                    
                    if len(image_bytes) < 1000:  # Minimum size check
                        logger.warning(f"[Stream B] Image too small (<1KB): {src}")
                        continue
                    
                    # Generate unique blob path
                    image_id = uuid.uuid4().hex[:8]
                    blob_path = f"patterns/{metadata['id']}/img_{image_id}.png"
                    
                    # Save to staging (local filesystem)
                    staging_image_dir = staging_dir / "images"
                    staging_image_dir.mkdir(exist_ok=True)
                    staging_file = staging_image_dir / f"img_{image_id}.png"
                    
                    with open(staging_file, 'wb') as f:
                        f.write(image_bytes)
                    
                    logger.debug(f"[Stream B] Staged image to {staging_file}")
                    
                    # Generate embedding
                    try:
                        emb = self.embed_model.get_embeddings(
                            image=Image(image_bytes),
                            context_text=f"Architecture diagram for {metadata['title']}"
                        ).image_embedding
                        
                        if not emb or len(emb) == 0:
                            logger.warning(f"[Stream B] Empty embedding for image: {src}")
                            continue
                        
                    except Exception as e:
                        logger.error(f"[Stream B] Failed to generate embedding for {src}: {e}")
                        continue
                    
                    # Prepare vector data
                    vector_id = f"img_{metadata['id']}_{image_id}"
                    gcs_uri = f"gs://{self.bucket.name}/{blob_path}"
                    
                    staged_images.append({
                        'staging_file': str(staging_file),
                        'blob_path': blob_path,
                        'gcs_uri': gcs_uri,
                        'image_bytes_size': len(image_bytes)
                    })
                    
                    vectors.append({
                        'id': vector_id,
                        'embedding': emb,
                        'payload': {
                            'pattern_id                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      ': metadata['id'],
                            'gcs_uri': gcs_uri,
                            'type': 'diagram',
                            'source_url': src
                        }
                    })
                    
                    logger.info(f"[Stream B] Prepared image {idx + 1}: {image_id}")
                    
                except Exception as e:
                    logger.error(f"[Stream B] Error processing image {src}: {e}")
                    # Continue with other images
                    continue
            
            # Validate we processed at least one image successfully
            if not staged_images:
                logger.warning(f"[Stream B] No images successfully processed for pattern {metadata['id']}")
                # This is not necessarily a failure - some patterns may not have diagrams
            
            # Save metadata to staging
            staging_meta = staging_dir / "stream_b_meta.json"
            with open(staging_meta, 'w') as f:
                json.dump({
                    'images': staged_images,
                    'vector_count': len(vectors),
                    'pattern_id': metadata['id']
                }, f, indent=2)
            
            logger.info(f"[Stream B] Prepared {len(staged_images)} images, {len(vectors)} vectors")
            
            return {
                'images': staged_images,
                'vectors': vectors,
                'pattern_id': metadata['id']
            }
            
        except Exception as e:
            logger.error(f"[Stream B] Preparation failed: {e}", exc_info=True)
            raise

    async def commit(self, prepared_data: Dict[str, Any]) -> None:
        """
        Phase 2: Upload images to GCS (with checksum) and upsert vectors to Vector Search (with timeout)
        """
        import asyncio
        import hashlib
        
        try:
            images = prepared_data['images']
            vectors = prepared_data['vectors']
            pattern_id = prepared_data['pattern_id']
            
            if not images:
                logger.info(f"[Stream B] No images to commit for pattern {pattern_id}")
                return
            
            logger.info(f"[Stream B] Committing {len(images)} images to GCS...")
            
            uploaded_blobs = []
            
            # Upload images to GCS with MD5 checksum verification
            for img_data in images:
                try:
                    staging_file = img_data['staging_file']
                    blob_path = img_data['blob_path']
                    
                    # Read file and compute MD5 checksum
                    with open(staging_file, 'rb') as f:
                        file_content = f.read()
                    
                    import base64
                    md5_hash = hashlib.md5(file_content).digest()
                    md5_b64 = base64.b64encode(md5_hash).decode('utf-8')
                    
                    blob = self.bucket.blob(blob_path)
                    blob.upload_from_filename(
                        staging_file, 
                        content_type="image/png",
                        checksum="md5"  # Enable server-side checksum verification
                    )
                    
                    uploaded_blobs.append(blob)
                    logger.debug(f"[Stream B] Uploaded {blob_path} (MD5 verified)")
                    
                except Exception as e:
                    logger.error(f"[Stream B] Failed to upload {blob_path}: {e}")
                    # Cleanup uploaded blobs and abort
                    for uploaded_blob in uploaded_blobs:
                        try:
                            uploaded_blob.delete()
                        except:
                            pass
                    raise
            
            logger.info(f"[Stream B] ✓ Uploaded {len(uploaded_blobs)} images to GCS")
            
            # Upsert vectors to Vector Search with timeout
            if vectors:
                logger.info(f"[Stream B] Upserting {len(vectors)} vectors to Vector Search...")
                try:
                    # Use retry logic with configurable timeout
                    await self._upsert_vectors_with_retry(vectors)
                    logger.info(f"[Stream B] ✓ Vectors upserted successfully")
                except Exception as e:
                    logger.error(f"[Stream B] Vector upsert failed: {e}")
                    # Cleanup GCS uploads on vector failure
                    for uploaded_blob in uploaded_blobs:
                        try:
                            uploaded_blob.delete()
                        except:
                            pass
                    raise
            
            logger.info(f"[Stream B] ✓ Commit completed for pattern {pattern_id}")
            
        except Exception as e:
            logger.error(f"[Stream B] Commit failed: {e}", exc_info=True)
            raise

    async def _upsert_vectors_with_retry(self, vectors: List[Dict[str, Any]], max_retries: int = 3) -> None:
        """Upsert vectors with retry logic and timeout"""
        import asyncio
        
        # Configurable timeout
        timeout = getattr(self.config, 'VECTOR_SEARCH_TIMEOUT', 180)
        
        for attempt in range(max_retries):
            try:
                await asyncio.wait_for(
                    self._upsert_vectors(vectors),
                    timeout=float(timeout)
                )
                return
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.warning(f"[Stream B] Vector upsert timed out (attempt {attempt + 1}), retrying...")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise Exception(f"Vector Search upsert timed out after {max_retries} attempts")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[Stream B] Vector upsert failed: {e}, retrying...")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    async def _upsert_vectors(self, vectors: List[Dict[str, Any]]) -> None:
        """
        Upsert vectors to Vertex AI Vector Search
        """
        try:
            # Prepare datapoints for Vector Search
            datapoints = []
            for vec in vectors:
                datapoint = aiplatform.matching_engine.MatchingEngineIndexEndpoint.Datapoint(
                    datapoint_id=vec['id'],
                    feature_vector=vec['embedding'],
                    restricts=[
                        aiplatform.matching_engine.MatchingEngineIndexEndpoint.Restriction(
                            namespace="pattern_id",
                            allow_list=[vec['payload']['pattern_id']]
                        )
                    ]
                )
                datapoints.append(datapoint)
            
            # Get index endpoint
            endpoint = aiplatform.MatchingEngineIndexEndpoint(self.index_endpoint)
            
            # Upsert datapoints
            endpoint.upsert_datapoints(
                deployed_index_id=self.deployed_index_id,
                datapoints=datapoints
            )
            
            logger.info(f"[Stream B] Successfully upserted {len(datapoints)} datapoints")
            
        except Exception as e:
            logger.error(f"[Stream B] Vector upsert failed: {e}", exc_info=True)
            raise

    async def rollback(self, prepared_data: Dict[str, Any]) -> None:
        """
        Rollback: Delete uploaded images from GCS and remove vectors
        """
        try:
            images = prepared_data.get('images', [])
            vectors = prepared_data.get('vectors', [])
            pattern_id = prepared_data['pattern_id']
            
            logger.warning(f"[Stream B] Rolling back pattern {pattern_id}...")
            
            # Delete images from GCS
            deleted_count = 0
            for img_data in images:
                try:
                    blob_path = img_data['blob_path']
                    blob = self.bucket.blob(blob_path)
                    blob.delete()
                    deleted_count += 1
                    logger.debug(f"[Stream B] Deleted blob: {blob_path}")
                except Exception as e:
                    logger.warning(f"[Stream B] Could not delete blob {img_data['blob_path']}: {e}")
            
            if deleted_count > 0:
                logger.info(f"[Stream B] ✓ Deleted {deleted_count} images from GCS")
            
            # Remove vectors from Vector Search
            if vectors:
                try:
                    vector_ids = [v['id'] for v in vectors]
                    endpoint = aiplatform.MatchingEngineIndexEndpoint(self.index_endpoint)
                    endpoint.remove_datapoints(
                        deployed_index_id=self.deployed_index_id,
                        datapoint_ids=vector_ids
                    )
                    logger.info(f"[Stream B] ✓ Removed {len(vector_ids)} vectors")
                except Exception as e:
                    logger.warning(f"[Stream B] Could not remove vectors: {e}")
            
            logger.info(f"[Stream B] ✓ Rollback completed")
            
        except Exception as e:
            logger.error(f"[Stream B] Rollback failed: {e}", exc_info=True)
            # Don't raise - best effort rollback