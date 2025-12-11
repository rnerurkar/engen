"""
Vision Agent - Handles image analysis and architectural visual processing.
"""

import os
import sys
import asyncio
import uvicorn

# Add serving-service to path for lib imports
serving_service_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if serving_service_dir not in sys.path:
    sys.path.insert(0, serving_service_dir)

from lib.adk_core import ADKAgent, AgentRequest, setup_logging
from lib.config import Config
from lib.prompts import PromptTemplates
from vertexai.generative_models import GenerativeModel, Part


class VisionAgent(ADKAgent):
    def __init__(self, port: int = 8081):
        super().__init__("VisionAgent", port=port)
        self.model = GenerativeModel("gemini-1.5-pro")

    async def process(self, request: AgentRequest) -> dict:
        uri = request.payload.get('image_uri') or request.payload.get('image')
        if not uri:
            raise ValueError("Missing 'image_uri' or 'image' in payload")
        
        # Use structured prompt from PromptTemplates
        prompt = PromptTemplates.vision_analyze_architecture_diagram()
        
        # Handle image bytes loading if not using GCS URI directly
        response = await self.model.generate_content_async(
            [Part.from_uri(uri, mime_type="image/png"), prompt]
        )
        
        return {"description": response.text, "desc": response.text}

    async def check_dependencies(self) -> dict:
        """Check Vertex AI availability"""
        try:
            # Basic check - model object exists
            if self.model:
                return {"vertex_ai": {"healthy": True, "critical": True}}
        except Exception as e:
            return {"vertex_ai": {"healthy": False, "critical": True, "error": str(e)}}
        return {}

    def get_supported_tasks(self):
        return ["interpret", "analyze", "describe"]

    def get_description(self):
        return "Analyzes architecture diagrams and extracts technical descriptions"


async def main():
    """Main entry point"""
    config = Config.get_agent_config("vision")
    setup_logging(config["log_level"])
    
    agent = VisionAgent(port=config["port"])
    await agent.start()
    await agent.run_async(port=config["port"])


if __name__ == "__main__":
    asyncio.run(main())

