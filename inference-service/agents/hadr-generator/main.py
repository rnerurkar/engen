import sys
import os

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/hadr-generator
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service

# Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
from core.pattern_synthesis.hadr_generator import HADRDocumentationGenerator


class HADRGeneratorAgent(ADKAgent):
    """
    Agent wrapper around HADRDocumentationGenerator core logic.

    Tasks:
      - generate_hadr_sections:      Generate all 4 DR strategy sections
                                     (async parallel via Gemini 1.5 Pro).
      - extract_donor_hadr_sections: Parse donor HTML to extract existing
                                     HA/DR sub-sections by strategy name.
    """

    def __init__(self):
        super().__init__(name="HADRGeneratorAgent", port=Config.HADR_GENERATOR_PORT)
        self.generator = HADRDocumentationGenerator(
            project_id=Config.PROJECT_ID,
            location=Config.LOCATION,
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")

        if req.task == "generate_hadr_sections":
            return await self._handle_generate(req)

        if req.task == "extract_donor_hadr_sections":
            return self._handle_extract_donor(req)

        return AgentResponse(
            status=TaskStatus.FAILED,
            error=f"Unknown task: {req.task}",
            agent_name=self.name,
        )

    # ─── Task handlers ───────────────────────────────────────────────────

    async def _handle_generate(self, req: AgentRequest) -> AgentResponse:
        """
        Payload:
          - pattern_context     (dict, required) — title, solution overview, services
          - donor_hadr_sections (dict, required) — strategy name → donor text
          - service_hadr_docs   (dict, required) — output of HADRRetrieverAgent
          - timeout_per_strategy (float, optional — default 120)
        """
        pattern_context = req.payload.get("pattern_context")
        donor_hadr_sections = req.payload.get("donor_hadr_sections")
        service_hadr_docs = req.payload.get("service_hadr_docs")

        if not pattern_context or donor_hadr_sections is None or service_hadr_docs is None:
            return AgentResponse(
                status=TaskStatus.FAILED,
                error="Missing required fields: pattern_context, donor_hadr_sections, service_hadr_docs",
                agent_name=self.name,
            )

        try:
            hadr_sections = await self.generator.agenerate_hadr_sections(
                pattern_context=pattern_context,
                donor_hadr_sections=donor_hadr_sections,
                service_hadr_docs=service_hadr_docs,
                timeout_per_strategy=req.payload.get("timeout_per_strategy", 120.0),
            )
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"hadr_sections": hadr_sections},
                agent_name=self.name,
            )
        except Exception as e:
            self.logger.error(f"HA/DR generation failed: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name,
            )

    def _handle_extract_donor(self, req: AgentRequest) -> AgentResponse:
        """
        Payload:
          - donor_html_content (str, required)
        """
        donor_html = req.payload.get("donor_html_content", "")

        try:
            sections = HADRDocumentationGenerator.extract_donor_hadr_sections(
                donor_html
            )
            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"donor_hadr_sections": sections},
                agent_name=self.name,
            )
        except Exception as e:
            self.logger.error(f"Donor extraction failed: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name,
            )


if __name__ == "__main__":
    agent = HADRGeneratorAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.HADR_GENERATOR_PORT)
