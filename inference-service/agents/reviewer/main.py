import sys
import os

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/reviewer
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service
codebase_root = os.path.dirname(inference_service_root) # .../codebase



# 2. Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
from core.reviewer import PatternReviewer

class PatternReviewerAgent(ADKAgent):
    def __init__(self):
        super().__init__(name="PatternReviewerAgent", port=Config.REVIEWER_PORT)
        self.reviewer = PatternReviewer(project_id=Config.PROJECT_ID)

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")
        
        if req.task == "review_pattern":
            try:
                sections = req.payload.get("sections")
                donor_context = req.payload.get("donor_context")
                
                if not sections or not donor_context:
                     return AgentResponse(
                        status=TaskStatus.FAILED,
                        error="Missing payload (sections, donor_context)",
                        agent_name=self.name
                    )

                critique = self.reviewer.review_pattern(sections, donor_context)
                
                return AgentResponse(
                    status=TaskStatus.COMPLETED,
                    result=critique,
                    agent_name=self.name
                )
                
            except Exception as e:
                self.logger.error(f"Reviewer error: {e}")
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=str(e),
                    agent_name=self.name
                )
        
        return AgentResponse(
            status=TaskStatus.FAILED,
            error=f"Unknown task: {req.task}",
            agent_name=self.name
        )

if __name__ == "__main__":
    agent = PatternReviewerAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.REVIEWER_PORT)
