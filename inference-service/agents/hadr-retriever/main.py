import sys
import os

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/hadr-retriever
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service

# Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
from core.pattern_synthesis.service_hadr_retriever import ServiceHADRRetriever


class HADRRetrieverAgent(ADKAgent):
    """
    Agent wrapper around ServiceHADRRetriever core logic.

    Tasks:
      - retrieve_service_hadr:     Retrieve HA/DR chunks for a single service.
      - retrieve_all_services_hadr: Retrieve HA/DR chunks for all services
                                    in the pattern (bulk).
    """

    def __init__(self):
        super().__init__(name="HADRRetrieverAgent", port=Config.HADR_RETRIEVER_PORT)
        self.retriever = ServiceHADRRetriever(
            project_id=Config.PROJECT_ID,
            location="global",
            data_store_id=Config.SERVICE_HADR_DATA_STORE_ID,
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")

        if req.task == "retrieve_service_hadr":
            return await self._handle_single_service(req)

        if req.task == "retrieve_all_services_hadr":
            return await self._handle_all_services(req)

        return AgentResponse(
            status=TaskStatus.FAILED,
            error=f"Unknown task: {req.task}",
            agent_name=self.name,
        )

    # ─── Task handlers ───────────────────────────────────────────────────

    async def _handle_single_service(self, req: AgentRequest) -> AgentResponse:
        """
        Payload:
          - service_name (str, required)
          - service_type (str, optional)
          - dr_strategy  (str, optional — filters to one DR strategy)
          - top_k        (int, optional — default 5)
        """
        service_name = req.payload.get("service_name")
        if not service_name:
            return AgentResponse(
                status=TaskStatus.FAILED,
                error="Missing 'service_name' in payload",
                agent_name=self.name,
            )

        try:
            chunks = await self.retriever.aretrieve_service_hadr_docs(
                service_name=service_name,
                service_type=req.payload.get("service_type"),
                dr_strategy=req.payload.get("dr_strategy"),
                top_k=req.payload.get("top_k", 5),
            )
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"chunks": chunks},
                agent_name=self.name,
            )
        except Exception as e:
            self.logger.error(f"Single-service retrieval failed: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name,
            )

    async def _handle_all_services(self, req: AgentRequest) -> AgentResponse:
        """
        Payload:
          - service_names (List[str], required)
          - service_types (Dict[str, str], optional)
        """
        service_names = req.payload.get("service_names")
        if not service_names:
            return AgentResponse(
                status=TaskStatus.FAILED,
                error="Missing 'service_names' in payload",
                agent_name=self.name,
            )

        try:
            all_docs = await self.retriever.aretrieve_all_services_hadr(
                service_names=service_names,
                service_types=req.payload.get("service_types"),
            )
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"service_hadr_docs": all_docs},
                agent_name=self.name,
            )
        except Exception as e:
            self.logger.error(f"Bulk retrieval failed: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name,
            )


if __name__ == "__main__":
    agent = HADRRetrieverAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.HADR_RETRIEVER_PORT)
