import sys
import os
import asyncio

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/hadr-diagram-generator
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service

# Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from config import Config
from core.pattern_synthesis.hadr_diagram_generator import (
    HADRDiagramGenerator,
    LIFECYCLE_PHASES,
)
from core.pattern_synthesis.hadr_diagram_storage import HADRDiagramStorage


class HADRDiagramGeneratorAgent(ADKAgent):
    """
    Agent wrapper around HADRDiagramGenerator + HADRDiagramStorage core logic.

    Tasks:
      - generate_and_store_hadr_diagrams:
            Generate SVG + draw.io XML diagrams for every DR strategy
            × lifecycle phase combination, upload to GCS, and return
            a URL map.
    """

    def __init__(self):
        super().__init__(
            name="HADRDiagramGeneratorAgent",
            port=Config.HADR_DIAGRAM_GENERATOR_PORT,
        )
        self.diagram_generator = HADRDiagramGenerator(
            project_id=Config.PROJECT_ID,
            location=Config.LOCATION,
        )
        self.diagram_storage = HADRDiagramStorage(
            bucket_name=Config.HADR_DIAGRAM_GCS_BUCKET,
            project_id=Config.PROJECT_ID,
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")

        if req.task == "generate_and_store_hadr_diagrams":
            return await self._handle_generate_and_store(req)

        return AgentResponse(
            status=TaskStatus.FAILED,
            error=f"Unknown task: {req.task}",
            agent_name=self.name,
        )

    # ─── Task handler ────────────────────────────────────────────────────

    async def _handle_generate_and_store(self, req: AgentRequest) -> AgentResponse:
        """
        Payload:
          - pattern_title        (str, required)
          - services             (List[str], required)
          - hadr_text_sections   (Dict[str, str], required)  — strategy → Markdown
          - pattern_context      (dict, required)
          - service_diagram_descriptions (dict, optional)
        """
        pattern_title = req.payload.get("pattern_title")
        services = req.payload.get("services")
        hadr_text_sections = req.payload.get("hadr_text_sections")
        pattern_context = req.payload.get("pattern_context")

        if not all([pattern_title, services, hadr_text_sections, pattern_context]):
            return AgentResponse(
                status=TaskStatus.FAILED,
                error="Missing required fields: pattern_title, services, hadr_text_sections, pattern_context",
                agent_name=self.name,
            )

        try:
            # 1. Generate all diagrams (async, semaphore-limited)
            bundle = await self.diagram_generator.agenerate_all_diagrams(
                pattern_name=pattern_title,
                services=services,
                hadr_text_sections=hadr_text_sections,
                pattern_context=pattern_context,
                service_diagram_descriptions=req.payload.get(
                    "service_diagram_descriptions"
                ),
            )

            # 2. Upload all diagram bundles to GCS in parallel
            async def _upload_one(strategy, phase, artifact):
                try:
                    urls = await self.diagram_storage.aupload_diagram_bundle(
                        pattern_name=pattern_title,
                        strategy=strategy,
                        phase=phase,
                        svg_content=artifact.svg_content,
                        drawio_xml=artifact.drawio_xml,
                        png_bytes=artifact.png_bytes,
                    )
                    return (strategy, phase), urls
                except Exception as exc:
                    self.logger.error(
                        f"Failed to upload diagram {strategy}/{phase}: {exc}"
                    )
                    return (strategy, phase), {}

            upload_tasks = [
                _upload_one(strategy, phase, artifact)
                for (strategy, phase), artifact in bundle.diagrams.items()
            ]
            upload_results = await asyncio.gather(
                *upload_tasks, return_exceptions=False
            )

            # 3. Build serialisable URL map (tuple keys → string keys)
            url_map = {}
            for (strategy, phase), urls in upload_results:
                url_map[f"{strategy}|{phase}"] = urls

            self.logger.info(
                f"Generated & stored {len(url_map)} diagram bundles for "
                f"'{pattern_title}'"
            )

            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={"diagram_urls": url_map},
                agent_name=self.name,
            )

        except Exception as e:
            self.logger.error(
                f"Diagram generation/storage failed: {e}", exc_info=True
            )
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name=self.name,
            )


if __name__ == "__main__":
    agent = HADRDiagramGeneratorAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.HADR_DIAGRAM_GENERATOR_PORT)
