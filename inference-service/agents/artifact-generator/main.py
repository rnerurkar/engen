import sys
import os
import asyncio
import logging

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/artifact-generator
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service

# Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
try:
    from component_specification_agent import ComponentSpecificationAgent
    from artifact_generation_agent import ArtifactGenerationAgent
except ImportError:
    # Fallback for when running from root 
    # Note: Python packages with dashes are problematic. 
    # Usually we'd rename artifact-generator to artifact_generator.
    # Assuming local import works for now.
    import importlib
    spec_mod = importlib.import_module("inference-service.agents.artifact-generator.component_specification_agent")
    art_mod = importlib.import_module("inference-service.agents.artifact-generator.artifact_generation_agent")
    ComponentSpecificationAgent = spec_mod.ComponentSpecificationAgent
    ArtifactGenerationAgent = art_mod.ArtifactGenerationAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedArtifactAgent(ADKAgent):
    """
    Unified Artifact Generation Agent handling both:
    1. Component Specification Extraction (Stage 3)
    2. Artifact Generation (Stage 4)
    """
    def __init__(self):
        super().__init__(name="UnifiedArtifactAgent", port=Config.ARTIFACT_PORT)
        
        # Initialize sub-agents
        self.spec_agent = ComponentSpecificationAgent()
        self.artifact_agent = ArtifactGenerationAgent()

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")
        
        try:
            if req.task == "generate_component_spec":
                # Process documentation to extract specs
                return self.spec_agent.process(req)
                
            elif req.task == "generate_artifact":
                # Generate artifact from specs
                return self.artifact_agent.process(req)
                
            else:
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=f"Unknown task: {req.task}",
                    agent_name=self.name
                )
        except Exception as e:
            self.logger.error(f"Error handling task {req.task}: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name
            )

if __name__ == "__main__":
    import uvicorn
    agent = UnifiedArtifactAgent()
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.ARTIFACT_PORT)
