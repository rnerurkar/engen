from core.pattern_synthesis.artifact_generator import ArtifactGenerator
from config import Config
from lib.adk_core import AgentRequest, AgentResponse, TaskStatus
import logging

logger = logging.getLogger(__name__)

class ArtifactGenerationAgent:
    """
    Agent wrapper around ArtifactGenerator core logic.
    """
    def __init__(self):
        self.engine = ArtifactGenerator(project_id=Config.PROJECT_ID)

    def process(self, req: AgentRequest) -> AgentResponse:
        # Expecting the full component specification and pattern documentation
        spec = req.payload.get("specification")
        documentation = req.payload.get("documentation")
        critique = req.payload.get("critique")
        
        if not spec or not documentation:
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error="Missing 'specification' or 'documentation' in payload", 
                agent_name="ArtifactGenerationAgent"
            )
            
        try:
            # Generate artifacts for the full pattern
            artifacts = self.engine.generate_full_pattern_artifacts(spec, documentation, critique)
            
            if "error" in artifacts:
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=artifacts["error"],
                    agent_name="ArtifactGenerationAgent"
                )
            
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"artifacts": artifacts},
                agent_name="ArtifactGenerationAgent"
            )
        except Exception as e:
            logger.error(f"Error in ArtifactGenerationAgent: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error=str(e), 
                agent_name="ArtifactGenerationAgent"
            )
