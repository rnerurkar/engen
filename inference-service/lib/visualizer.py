import base64
import zlib
import requests
import logging
import os

logger = logging.getLogger(__name__)

class DiagramRenderer:
    """
    Handles converting Mermaid.js code blocks into image bytes.
    Supports local self-hosted Kroki instance or public API.
    """
    def __init__(self):
        # Default to internal Docker service name if running in Cloud Run/K8s
        # Fallback to localhost for dev, or public API if configured.
        self.kroki_endpoint = os.getenv("KROKI_ENDPOINT", "http://localhost:8000")
        logger.info(f"Initialized DiagramRenderer with endpoint: {self.kroki_endpoint}")

    def render_mermaid(self, mermaid_code: str) -> bytes:
        """
        Converts Mermaid code to a PNG image using the Kroki API.
        
        Args:
            mermaid_code: The raw mermaid script (e.g., "graph TD; A-->B;")
            
        Returns:
            The binary content of the PNG image.
        """
        try:
            # 1. Compress the diagram code using zlib
            compressed_data = zlib.compress(mermaid_code.encode('utf-8'))
            
            # 2. Base64 encode the result (URL-safe)
            # Kroki requires standard base64 but with URL-safe chars (-_) 
            # instead of (+/) and no padding.
            payload = base64.urlsafe_b64encode(compressed_data).decode('utf-8')
            
            # 3. Construct the API URL
            # Format: {endpoint}/mermaid/png/{payload}
            url = f"{self.kroki_endpoint}/mermaid/png/{payload}"
            
            # 4. Fetch the image
            response = requests.get(url, timeout=10) # 10s timeout
            if response.status_code == 200:
                logger.info("Successfully rendered Mermaid diagram to PNG")
                return response.content
            else:
                logger.error(f"Kroki Rendering Failed: {response.status_code} - {response.text}")
                # Fallback: Return empty bytes or raise? Raising is safer to detect failure.
                raise Exception(f"Kroki Rendering Failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error in diagram rendering: {e}")
            raise e
