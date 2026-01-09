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


"""
Writer Agent - The content creator.
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
from vertexai.generative_models import GenerativeModel


class WriterAgent(ADKAgent):
    """
    The Writer Agent is the "Author" of the system.
    
    SYSTEM DESIGN: One-Shot Generator + Refiner
    -------------------------------------------
    This agent takes the raw materials and synthesizes them into a polished document section.
    
    The "Secret Sauce":
    1. It mimics a human expert ("Donor Pattern").
    2. It adapts to the user's specific diagram.
    3. It improves based on feedback ("Critique").
    
    Why separate Writer from Reviewer?
    Separate agents allow for "Adversarial Improvement". The Writer tries to please the Reviewer,
    and the Reviewer tries to find faults. This produces better quality than a single agent checking itself.
    """
    def __init__(self, port: int = 8083):
        super().__init__("WriterAgent", port=port)
        # Using Gemini 1.5 Pro because writing requires high verbal intelligence and context window
        self.model = GenerativeModel("gemini-1.5-pro")

    async def process(self, request: AgentRequest) -> dict:
        """
        Generates or Refines a single section of the document.
        
        Inputs:
        - section: "Problem" (The topic to write)
        - description: "This is a 3-tier app..." (The context)
        - donor_context: "The donor pattern says..." (The style guide/reference)
        - critique: "Too vague. Explain the database." (Feedback from Reviewer, optional)
        """
        sec = request.payload.get('section', 'Overview')
        desc = request.payload.get('description', '')
        donor_context = request.payload.get('donor_context', {})
        
        # Extract the specific section text from the donor pattern to use as a "Style Reference"
        ref = donor_context.get('sections', {}).get(sec, {}).get('plain_text', '')
        
        critique = request.payload.get('critique', '')

        # Use structured prompt from PromptTemplates
        # This dynamically assembles the prompt (Strategy Pattern) based on section type
        prompt = PromptTemplates.writer_generate_section(
            section_name=sec,
            description=desc,
            reference_text=ref, # "Write LIKE this..."
            critique=critique   # "...but fix THIS error."
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

