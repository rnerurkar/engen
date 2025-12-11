"""
Reviewer Agent - Handles quality review and validation.
"""

import os
import sys
import asyncio
import uvicorn
import json
import re

# Add serving-service to path for lib imports
serving_service_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if serving_service_dir not in sys.path:
    sys.path.insert(0, serving_service_dir)

from lib.adk_core import ADKAgent, AgentRequest, setup_logging
from lib.config import Config
from lib.prompts import PromptTemplates
from vertexai.generative_models import GenerativeModel


class ReviewerAgent(ADKAgent):
    def __init__(self, port: int = 8084):
        super().__init__("ReviewerAgent", port=port)
        self.model = GenerativeModel("gemini-1.5-pro")

    async def process(self, request: AgentRequest) -> dict:
        draft = request.payload.get('draft', '')
        if isinstance(draft, dict):
            draft = draft.get('text', str(draft))
        
        # Use structured prompt from PromptTemplates
        prompt = PromptTemplates.reviewer_evaluate_draft(draft_text=draft)
        
        response = await self.model.generate_content_async(prompt)
        return self._parse_review_response(response.text)

    async def check_dependencies(self) -> dict:
        """Check Vertex AI availability"""
        try:
            if self.model:
                return {"vertex_ai": {"healthy": True, "critical": True}}
        except Exception as e:
            return {"vertex_ai": {"healthy": False, "critical": True, "error": str(e)}}
        return {}

    def _parse_review_response(self, response_text: str) -> dict:
        """Robustly parse LLM response to extract score and feedback"""
        # Try direct JSON parse first
        try:
            # Remove markdown code blocks if present
            clean_text = response_text.strip()
            clean_text = re.sub(r'^```json\s*', '', clean_text)
            clean_text = re.sub(r'^```\s*', '', clean_text)
            clean_text = re.sub(r'\s*```$', '', clean_text)
            clean_text = clean_text.strip()
            
            result = json.loads(clean_text)
            if 'score' in result and 'feedback' in result:
                return result
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from response
        try:
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                if 'score' in result:
                    return result
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Extract score using regex
        score_match = re.search(r'score["\']?\s*[:=]\s*(\d+)', response_text, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 50
        
        # Extract feedback - take first substantial sentence
        feedback = "Review completed. See full response for details."
        sentences = re.split(r'[.!?]', response_text)
        for sentence in sentences:
            clean = sentence.strip()
            if len(clean) > 20 and 'json' not in clean.lower():
                feedback = clean + "."
                break
        
        return {"score": min(100, max(0, score)), "feedback": feedback}

    def get_supported_tasks(self):
        return ["review", "evaluate", "score"]

    def get_description(self):
        return "Reviews technical documentation for quality and accuracy"


async def main():
    """Main entry point"""
    config = Config.get_agent_config("reviewer")
    setup_logging(config["log_level"])
    
    agent = ReviewerAgent(port=config["port"])
    await agent.start()
    await agent.run_async(port=config["port"])


if __name__ == "__main__":
    asyncio.run(main())