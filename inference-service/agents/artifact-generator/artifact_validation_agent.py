from core.pattern_synthesis.artifact_validator import ArtifactValidator
from config import Config
from lib.adk_core import AgentRequest, AgentResponse, TaskStatus
import logging

logger = logging.getLogger(__name__)

class ArtifactValidationAgent:
    """
    Agent wrapper around ArtifactValidator core logic (Pattern Synthesis).
    """
    def __init__(self):
        self.engine = ArtifactValidator(project_id=Config.PROJECT_ID)

    def process(self, req: AgentRequest) -> AgentResponse:
        artifacts = req.payload.get("artifacts")
        component_spec = req.payload.get("component_spec")
        
        if not artifacts:
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error="Missing 'artifacts' in payload", 
                agent_name="ArtifactValidationAgent"
            )
        
        if not component_spec:
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error="Missing 'component_spec' in payload", 
                agent_name="ArtifactValidationAgent"
            )
            
        try:
            result = self.engine.validate_artifacts(artifacts, component_spec)
            
            # The result now contains the score and detailed feedback
            status = TaskStatus.COMPLETED if result.get("status") == "PASS" else TaskStatus.FAILED_RETRYABLE
            
            api_resp = AgentResponse(
                status=status,
                result={
                    "validation_result": result
                },
                agent_name="ArtifactValidationAgent"
            )
            return api_resp

        except Exception as e:
            logger.error(f"Error in ArtifactValidationAgent: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error=str(e), 
                agent_name="ArtifactValidationAgent"
            )
