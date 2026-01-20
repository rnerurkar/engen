import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PatternGenerator:
    """
    Uses Gemini 1.5 Pro to perform 'One-Shot' generation.
    It looks at an input diagram, reads a donor pattern's HTML, 
    and generates a NEW pattern that matches the donor's style exactly.
    """
    def __init__(self, project_id: str, location: str = "us-central1"):
        vertexai.init(project=project_id, location=location)
        # Using 1.5 Pro for maximum context window and instruction following
        self.model = GenerativeModel("gemini-1.5-pro-preview-0409", 
                                     system_instruction="You are a Principal Software Architect.")

    def generate_search_description(self, image_bytes: bytes) -> str:
        """
        Step 1 Helper: Generates a technical description of the input diagram 
        to be used as part of the search query for the Retriever.
        """
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        
        prompt = """
        Analyze this technical architecture diagram.
        Provide a concise description of the structural design, key components, and data flow.
        Focus on identifying the architectural pattern depicted (e.g., Event-Driven, Layered, Microservices).
        This description will be used to search for similar reference patterns.
        """

        try:
            response = self.model.generate_content(
                [prompt, image_part],
                generation_config={"max_output_tokens": 256, "temperature": 0.0}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Image description generation failed: {e}")
            # Fallback to empty string so reliance is solely on title
            return ""

    def generate_pattern(self, image_bytes: bytes, donor_context: Dict[str, str], user_title: str, critique: str = None) -> Dict[str, str]:
        """
        Generates the full pattern content in JSON format matching the SharePoint publisher schema.
        """
        
        # 1. Prepare Multimodal Inputs
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        
        donor_html = donor_context.get("html_content", "")
        
        # 2. Construct the PROMPT
        # Note: We ask for JSON output so we can map it to SharePoint sections easily.
        prompt = f"""
        TASK:
        Analyze the provided technical architecture diagram (Image) and generate a comprehensive 
        Software Design Pattern document for the concept: "{user_title}".

        STYLE REFERENCE:
        You must strictly follow the tone, depth, and structural organization of the 
        Reference Pattern provided below. Mimic its use of headers, lists, and technical vocabulary.
        """

        if critique:
            prompt += f"""
            IMPROVEMENT INSTRUCTIONS:
            This is an iterative improvement of a previous draft. 
            The Reviewer Agent provided the following CRITIQUE which you MUST address:
            "{critique}"
            
            Focus heavily on fixing the issues mentioned above while maintaining the reference style.
            """

        prompt += f"""
        DIAGRAM INSTRUCTIONS:
        If the Donor Pattern contains a diagram in a specific section, you MUST generate a corresponding 
        diagram for the new pattern in that SAME section.
        - Use `mermaid` code blocks for diagrams. (e.g., ```mermaid graph TD; ... ```)
        - The diagram structure should mimic the donor's complexity but reflect the components of the INPUT IMAGE.
        
        REFERENCE PATTERN HTML (Start):
        {donor_html}
        REFERENCE PATTERN HTML (End)

        OUTPUT FORMAT:
        Return a valid JSON object where keys are Section Headers (e.g., "Problem", "Solution", "Components")
        and values are the Markdown/HTML content for that section.
        Do not include the 'Document Metadata' or 'AI Generated Description' sections.
        
        Example Output:
        {{
            "Executive Summary": "...",
            "Problem Statement": "...",
            "Solution Architecture": "..."
        }}
        """

        # 3. Inference
        try:
            response = self.model.generate_content(
                [prompt, image_part],
                generation_config={"response_mime_type": "application/json", "temperature": 0.2}
            )
            
            # Simple cleanup if the model wraps in markdown code blocks
            text_res = response.text.strip()
            if text_res.startswith("```json"):
                text_res = text_res[7:]
            if text_res.endswith("```"):
                text_res = text_res[:-3]
                
            return json.loads(text_res)
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
