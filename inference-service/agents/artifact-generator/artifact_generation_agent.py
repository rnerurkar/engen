from core.artifact_generator import ArtifactGenerator
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
        spec = req.payload.get("specification")
        artifact_type = req.payload.get("artifact_type", "terraform")
        
        if not spec:
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error="Missing 'specification' in payload", 
                agent_name="ArtifactGenerationAgent"
            )
            
        try:
            artifact = self.engine.generate_artifact(spec, artifact_type)
            if not self.engine.validate_artifact(artifact):
                return AgentResponse(
                    status=TaskStatus.FAILED, 
                    error="Validation failed", 
                    agent_name="ArtifactGenerationAgent"
                )
            
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"artifact": artifact},
                agent_name="ArtifactGenerationAgent"
            )
        except Exception as e:
            logger.error(f"Error in ArtifactGenerationAgent: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error=str(e), 
                agent_name="ArtifactGenerationAgent"
            )
