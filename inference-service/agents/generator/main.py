import sys
import os
import base64

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/generator
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service
codebase_root = os.path.dirname(inference_service_root) # .../codebase



# 2. Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
from core.generator import PatternGenerator

class PatternGeneratorAgent(ADKAgent):
    def __init__(self):
        super().__init__(name="PatternGeneratorAgent", port=Config.GENERATOR_PORT)
        self.generator = PatternGenerator(project_id=Config.PROJECT_ID)

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")
        
        if req.task == "describe_image":
            try:
                image_b64 = req.payload.get("image_base64")
                if not image_b64:
                    return AgentResponse(
                        status=TaskStatus.FAILED,
                        error="Missing image_base64",
                        agent_name=self.name
                    )

                image_bytes = base64.b64decode(image_b64)
                description = self.generator.generate_search_description(image_bytes)
                
                return AgentResponse(
                    status=TaskStatus.COMPLETED,
                    result={"description": description},
                    agent_name=self.name
                )
            except Exception as e:
                 self.logger.error(f"Description generation error: {e}")
                 return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=str(e),
                    agent_name=self.name
                )

        if req.task == "generate_pattern":
            try:
                # Extract payload
                image_b64 = req.payload.get("image_base64")
                donor_context = req.payload.get("donor_context")
                title = req.payload.get("title")
                critique = req.payload.get("critique")
                
                if not all([image_b64, donor_context, title]):
                     return AgentResponse(
                        status=TaskStatus.FAILED,
                        error="Missing required payload fields (image_base64, donor_context, title)",
                        agent_name=self.name
                    )

                # Decode image
                image_bytes = base64.b64decode(image_b64)
                
                # Run Generation
                generated_sections = self.generator.generate_pattern(
                    image_bytes=image_bytes,
                    donor_context=donor_context,
                    user_title=title,
                    critique=critique
                )
                
                return AgentResponse(
                    status=TaskStatus.COMPLETED,
                    result={"sections": generated_sections},
                    agent_name=self.name
                )
                
            except Exception as e:
                self.logger.error(f"Generator error: {e}")
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
    agent = PatternGeneratorAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.GENERATOR_PORT)
