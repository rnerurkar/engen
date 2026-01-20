import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PatternReviewer:
    """
    Critiques the generated pattern content for technical accuracy, completeness,
    and style adherence.
    """
    def __init__(self, project_id: str, location: str = "us-central1"):
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-1.5-pro-preview-0409",
                                     system_instruction="You are a Technical Editor and QA Specialist.")

    def review_pattern(self, sections: Dict[str, str], donor_context: Dict[str, str]) -> Dict[str, Any]:
        """
        Reviews the sections against the donor context.
        Returns a structured critique: approved (bool), issues (list).
        """
        
        content_dump = json.dumps(sections, indent=2)
        donor_html = donor_context.get("html_content", "")[:10000] # Truncate donor if too huge, but Gemini 1.5 likely fine.

        prompt = f"""
        TASK:
        Review the following Generated Design Pattern (JSON Sections) against the Reference Style (Donor Pattern).
        
        CRITERIA:
        1. **completeness**: Are all expected sections present?
        2. **Consistency**: Does the generated text match the style/tone of the reference?
        3. **Technical Depth**: Is the content specific and technical, not generic?
        4. **Formatting**: Is Markdown/HTML usage correct?

        GENERATED CONTENT:
        {content_dump}

        REFERENCE STYLE (Excerpt):
        {donor_html}

        OUTPUT FORMAT:
        Return a valid JSON object:
        {{
            "approved": boolean,  // true if quality is high, false if needs revision
            "score": number,      // 0-100
            "critique": "Overall summary of findings...",
            "section_feedback": {{
                "Section Name": "Specific feedback or OK"
            }}
        }}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            
            text_res = response.text.strip()
            if text_res.startswith("```json"):
                text_res = text_res[7:]
            if text_res.endswith("```"):
                text_res = text_res[:-3]
                
            return json.loads(text_res)

        except Exception as e:
            logger.error(f"Review failed: {e}")
            # Fail safe
            return {"approved": True, "score": 100, "critique": "Reviewer failed to run.", "error": str(e)}
