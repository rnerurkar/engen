"""
Example: Updated Writer Agent Implementation
Demonstrates proper use of enhanced ADK and prompt templates
"""

import asyncio
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib import (
    ADKAgent, 
    AgentRequest, 
    PromptTemplates,
    setup_logging
)
from vertexai.generative_models import GenerativeModel
from typing import List


class WriterAgent(ADKAgent):
    """
    Enhanced Writer Agent using ADK best practices
    """
    
    def __init__(self):
        super().__init__(
            name="WriterAgent",
            port=8083,
            version="2.0.0"
        )
        self.model = None  # Initialize in async initialize()
    
    async def initialize(self):
        """Initialize the Vertex AI model during startup"""
        self.logger.info("Initializing Vertex AI Gemini model...")
        self.model = GenerativeModel("gemini-1.5-pro")
        self.logger.info("Model initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources during shutdown"""
        self.logger.info("Cleaning up Writer Agent resources...")
        # Close any open connections, save state, etc.
    
    def get_supported_tasks(self) -> List[str]:
        """Declare supported task types"""
        return [
            "write_section",
            "generate_problem_statement",
            "generate_solution_overview",
            "generate_implementation_details",
            "generate_tradeoffs"
        ]
    
    def get_description(self) -> str:
        """Provide agent description"""
        return (
            "Writer Agent generates high-quality technical documentation sections "
            "for software architecture diagrams using AI-powered content generation."
        )
    
    async def process(self, req: AgentRequest) -> dict:
        """
        Main processing logic for Writer Agent
        
        Expected payload structure:
        {
            "section": "Problem|Solution|Implementation|Trade-offs",
            "description": "System description from vision analysis",
            "donor_context": {
                "sections": {
                    "section_name": {"plain_text": "...", ...}
                }
            },
            "critique": "Optional feedback from reviewer" (optional)
        }
        """
        # Extract payload
        section = req.payload.get('section', 'Problem')
        description = req.payload.get('description', '')
        donor_context = req.payload.get('donor_context', {})
        critique = req.payload.get('critique', '')
        
        # Get reference content for this section
        sections = donor_context.get('sections', {})
        reference_content = sections.get(section, {}).get('plain_text', '')
        
        if not reference_content:
            self.logger.warning(
                f"No reference content found for section '{section}', "
                "using generic template"
            )
            reference_content = "Write in a clear, professional technical style."
        
        # Build prompt using template
        prompt = PromptTemplates.writer_generate_section(
            section_name=section,
            description=description,
            reference_content=reference_content,
            critique=critique,
            context=req.context
        )
        
        # Log prompt for debugging (first 200 chars)
        self.logger.debug(f"Generated prompt: {prompt[:200]}...")
        
        # Generate content using Vertex AI
        self.logger.info(f"Generating content for section: {section}")
        response = await self.model.generate_content_async(prompt)
        
        generated_text = response.text
        
        # Log result
        self.logger.info(
            f"Generated {len(generated_text)} characters for section '{section}'"
        )
        
        return {
            "section": section,
            "text": generated_text,
            "word_count": len(generated_text.split()),
            "char_count": len(generated_text),
            "model": "gemini-1.5-pro",
            "has_critique": bool(critique)
        }


async def main():
    """
    Main entry point - simplified using ADK
    """
    setup_logging(level="INFO")
    
    agent = WriterAgent()
    
    # The agent.run() method handles uvicorn startup
    agent.run(host="0.0.0.0", port=8083)


if __name__ == "__main__":
    asyncio.run(main())
