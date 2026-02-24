from core.pattern_synthesis.component_specification import ComponentSpecification
from config import Config
from lib.adk_core import AgentRequest, AgentResponse, TaskStatus
import logging

logger = logging.getLogger(__name__)

class ComponentSpecificationAgent:
    """
    Agent wrapper around ComponentSpecification core logic.
    """
    def __init__(self):
        self.engine = ComponentSpecification(project_id=Config.PROJECT_ID)

    def process(self, req: AgentRequest) -> AgentResponse:
        documentation = req.payload.get("documentation")
        if not documentation:
             return AgentResponse(
                status=TaskStatus.FAILED, 
                error="Missing 'documentation' in payload", 
                agent_name="ComponentSpecificationAgent"
            )
            
        try:
            # Process documentation to get comprehensive spec with execution order
            specs = self.engine.process_documentation(documentation)
            
            # Validation logic can be added here or inside the engine
            if "error" in specs:
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=specs["error"],
                    agent_name="ComponentSpecificationAgent"
                )
            
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={
                    "specifications": specs, # Contains components, relationships, execution_order
                    "execution_plan": specs.get("execution_order", [])
                },
                agent_name="ComponentSpecificationAgent"
            )
        except Exception as e:
            logger.error(f"Error in ComponentSpecificationAgent: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED, 
                error=str(e), 
                agent_name="ComponentSpecificationAgent"
            )
