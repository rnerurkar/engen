import sys
import os
import asyncio

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/retriever
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service
codebase_root = os.path.dirname(inference_service_root) # .../codebase



# 2. Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
from core.retriever import VertexRetriever

class PatternRetrieverAgent(ADKAgent):
    def __init__(self):
        super().__init__(name="PatternRetrieverAgent", port=Config.RETRIEVER_PORT)
        # Initialize Core Logic
        self.retriever = VertexRetriever(
            project_id=Config.PROJECT_ID, 
            location="global", # Search often global
            data_store_id=Config.DATA_STORE_ID
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")
        
        if req.task == "retrieve_donor":
            query = req.payload.get("title")
            description = req.payload.get("description", "")
            
            if not query:
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error="Missing 'title' in payload",
                    agent_name=self.name
                )
            
            result = self.retriever.get_best_donor_pattern(query, description)
            
            if result:
                return AgentResponse(
                    status=TaskStatus.COMPLETED,
                    result=result,
                    agent_name=self.name
                )
            else:
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error="No matching pattern found",
                    agent_name=self.name
                )
        
        return AgentResponse(
            status=TaskStatus.FAILED,
            error=f"Unknown task: {req.task}",
            agent_name=self.name
        )

if __name__ == "__main__":
    agent = PatternRetrieverAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.RETRIEVER_PORT)
