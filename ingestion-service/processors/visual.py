from google.cloud import storage
from vertexai.vision_models import MultiModalEmbeddingModel, Image
from bs4 import BeautifulSoup
import uuid

class StreamBProcessor:
    def __init__(self, config, sp_client):
        self.embed_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")
        self.bucket = storage.Client().bucket(config.GCS_BUCKET)
        self.sp_client = sp_client # Need SP client to download private images
        # Vector Search Client (gRPC) setup omitted for brevity; assumes standard Upsert logic

    def process(self, metadata, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        vectors = []
        
        # 1. Find Diagram Images
        # Heuristic: Find images in the 'Solution' section or large images
        imgs = soup.find_all('img')
        
        for img in imgs:
            src = img.get('src')
            if not src or "icon" in src.lower(): continue

            # 2. Download from SharePoint
            image_bytes = self.sp_client.download_image(src)
            if not image_bytes: continue

            # 3. Upload to GCS
            blob_path = f"patterns/{metadata['id']}/{uuid.uuid4()}.png"
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(image_bytes, content_type="image/png")
            gcs_uri = f"gs://{self.bucket.name}/{blob_path}"

            # 4. Generate Embedding
            emb = self.embed_model.get_embeddings(
                image=Image(image_bytes),
                context_text=f"Architecture diagram for {metadata['title']}"
            ).image_embedding

            # 5. Prepare Vector Payload (Linking Visual -> Text Sections)
            # In a real run, we'd map this specific image to its parent section ID
            vectors.append({
                "id": f"img_{metadata['id']}_{uuid.uuid4().hex[:6]}",
                "embedding": emb,
                "payload": {
                    "pattern_id": metadata['id'],
                    "gcs_uri": gcs_uri,
                    "type": "diagram"
                }
            })
            
        # 6. Upsert to Vertex Vector Search (Pseudo-code for library call)
        # self.vector_client.upsert(vectors)
        return vectors