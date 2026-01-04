import logging
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Image
from bs4 import BeautifulSoup
from markdownify import markdownify

logger = logging.getLogger(__name__)

class ContentProcessor:
    def __init__(self, project_id: str, location: str, sp_client):
        self.sp_client = sp_client
        vertexai.init(project=project_id, location=location)
        self.vision_model = GenerativeModel("gemini-pro-vision")
        logger.info("Vertex AI Gemini Pro Vision initialized.")

    def _describe_image(self, image_bytes: bytes) -> str:
        """Sends image bytes to Gemini Pro Vision for description."""
        prompt = "Analyze this technical architecture diagram or screenshot. Describe the data flow, components involved, protocols, and any specific configurations depicted in technical detail."
        try:
            response = self.vision_model.generate_content([prompt, Image.from_bytes(image_bytes)])
            return response.text
        except Exception as e:
            logger.error(f"Error generating image description with Vertex AI: {e}")
            return "Image description unavailable due to processing error."

    def process_html_to_markdown(self, html_content: str, base_url: str) -> str:
        """Cleans HTML, enriches images with AI descriptions, converts to Markdown."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Target main content div (adjust selector based on your SP version)
        # Common selectors: div[id='CanvasZone'], div[class*='CanvasComponent']
        main_content = soup.find('div', id='CanvasZone') 
        if not main_content:
            main_content = soup # Fallback if specific zone not found

        # 2. Multimodal Enrichment
        images = main_content.find_all('img')
        logger.info(f"Found {len(images)} images to process.")
        
        for img in images:
            img_src = img.get('src')
            if not img_src: continue
            
            # Handle relative URLs if necessary
            full_img_url = img_src if img_src.startswith('http') else f"{base_url}{img_src}"

            logger.debug(f"Processing image: {full_img_url}")
            image_bytes = self.sp_client.download_image_bytes(full_img_url)
            
            if image_bytes:
                description = self._describe_image(image_bytes)
                # Replace image tag with a detailed text block
                new_text_node = soup.new_tag("blockquote")
                new_text_node.string = f"**[Detailed Diagram Description]:** {description}"
                img.replace_with(new_text_node)
            else:
                 img.decompose() # Remove broken images

        # 3. Clean and Convert to Markdown
        # Remove unwanted elements
        for script in main_content(["script", "style", "noscript"]):
            script.decompose()

        cleaned_html = str(main_content)
        markdown_text = markdownify(cleaned_html, heading_style="ATX")
        return markdown_text