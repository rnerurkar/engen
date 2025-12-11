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
from vertexai.generative_models import GenerativeModel


class WriterAgent(ADKAgent):
    def __init__(self, port: int = 8083):
        super().__init__("WriterAgent", port=port)
        self.model = GenerativeModel("gemini-1.5-pro")

    async def process(self, request: AgentRequest) -> dict:
        sec = request.payload.get('section', 'Overview')
        desc = request.payload.get('description', '')
        donor_context = request.payload.get('donor_context', {})
        ref = donor_context.get('sections', {}).get(sec, {}).get('plain_text', '')
        critique = request.payload.get('critique', '')

        # Use structured prompt from PromptTemplates
        prompt = PromptTemplates.writer_generate_section(
            section_name=sec,
            description=desc,
            reference_text=ref,
            critique=critique
        )
        
        response = await self.model.generate_content_async(prompt)
        return {"text": response.text}

    async def check_dependencies(self) -> dict:
        """Check Vertex AI availability"""
        try:
            if self.model:
                return {"vertex_ai": {"healthy": True, "critical": True}}
        except Exception as e:
            return {"vertex_ai": {"healthy": False, "critical": True, "error": str(e)}}
        return {}

    def get_supported_tasks(self):
        return ["write", "draft", "revise"]

    def get_description(self):
        return "Generates technical documentation sections based on architecture descriptions"


async def main():
    """Main entry point"""
    config = Config.get_agent_config("writer")
    setup_logging(config["log_level"])
    
    agent = WriterAgent(port=config["port"])
    await agent.start()
    await agent.run_async(port=config["port"])


if __name__ == "__main__":
    asyncio.run(main())

