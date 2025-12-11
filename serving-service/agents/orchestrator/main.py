"""
Orchestrator Agent
------------------

Coordinates the agent workflow and optionally publishes the final document to
SharePoint using `SharePointPublisher`.

SharePoint Publishing Notes:
- Markdown conversion uses Python-Markdown with extensions (fenced_code, tables,
    sane_lists, codehilite, toc) rather than custom regex.
- Resulting HTML is sanitized with Bleach (allowlisted tags/attrs/protocols)
    before embedding into a SharePoint Text web part as `properties.inlineHtml`.
- See `serving-service/lib/sharepoint_publisher.py` for implementation details.
"""
import os
import sys
import asyncio
import aiohttp

# Add the serving-service directory to Python path to access lib
serving_service_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if serving_service_dir not in sys.path:
    sys.path.insert(0, serving_service_dir)

from lib.adk_core import ADKAgent, AgentRequest, setup_logging
from lib.config import Config
from lib.a2a_client import A2AClient, A2AError
from lib.sharepoint_publisher import SharePointPublisher, SharePointPageConfig


class Orchestrator(ADKAgent):
    def __init__(self, port: int = 8080, config: dict = None):
        super().__init__("Orchestrator", port=port)
        self.config = config or {}
        
        # Agent URLs from config or environment
        self.vis_url = os.getenv("VISION_URL") or self.config.get("vision_url", "http://localhost:8081")
        self.ret_url = os.getenv("RETRIEVAL_URL") or self.config.get("retrieval_url", "http://localhost:8082")
        self.writ_url = os.getenv("WRITER_URL") or self.config.get("writer_url", "http://localhost:8083")
        self.rev_url = os.getenv("REVIEWER_URL") or self.config.get("reviewer_url", "http://localhost:8084")
        
        # Configuration
        self.max_revisions = int(os.getenv("MAX_REVISIONS", 3))
        self.min_score = int(os.getenv("MIN_REVIEW_SCORE", 90))
        self.timeout = int(os.getenv("AGENT_TIMEOUT", 60))
        
        # SharePoint publishing configuration
        self.publish_to_sharepoint = os.getenv("PUBLISH_TO_SHAREPOINT", "false").lower() == "true"
        self.sp_publisher = None
        
        if self.publish_to_sharepoint:
            sp_config = SharePointPageConfig.from_env()
            if sp_config.is_valid():
                self.sp_publisher = SharePointPublisher(sp_config)
                self.logger.info("SharePoint publisher initialized")
            else:
                self.logger.warning("SharePoint publishing enabled but credentials not configured")
                self.publish_to_sharepoint = False

    async def process(self, req: AgentRequest) -> dict:
        """Process architecture diagram through the agent pipeline"""
        img = req.payload.get('image') or req.payload.get('image_uri')
        if not img:
            raise ValueError("Missing 'image' or 'image_uri' in payload")
        
        # Get optional parameters
        title = req.payload.get('title', 'Architecture Documentation')
        should_publish = req.payload.get('publish', self.publish_to_sharepoint)
        
        self.logger.info(f"Processing diagram: {img}")
        self.logger.info(f"Title: {title}, Publish to SharePoint: {should_publish}")
        
        # Use A2AClient for all agent communication
        async with A2AClient("Orchestrator", default_timeout=self.timeout) as client:
            
            # 1. Vision - Analyze the diagram
            self.logger.info("Step 1: Analyzing diagram with Vision agent...")
            try:
                vis = await client.call_agent(self.vis_url, "interpret", {"image": img})
                description = vis.get('description') or vis.get('desc', '')
                
                if not description:
                    raise ValueError("Vision agent returned empty description")
                
                self.logger.info(f"Vision analysis complete: {len(description)} chars")
            except A2AError as e:
                self.logger.error(f"Vision agent failed: {e}")
                raise
            
            # 2. Retrieval - Find similar patterns
            self.logger.info("Step 2: Finding donor patterns with Retrieval agent...")
            try:
                ret = await client.call_agent(self.ret_url, "find_donor", {
                    "description": description,
                    "image": img
                })
                
                donor_id = ret.get('donor_id')
                self.logger.info(f"Found donor pattern: {donor_id}")
            except A2AError as e:
                self.logger.error(f"Retrieval agent failed: {e}")
                raise
            
            # 3. Reflection Loop - Write and review sections
            sections_to_generate = req.payload.get('sections', ["Problem", "Solution"])
            final_doc = {}
            
            for sec in sections_to_generate:
                self.logger.info(f"Step 3: Generating section '{sec}'...")
                critique = ""
                
                for revision in range(self.max_revisions):
                    # Write draft
                    try:
                        draft = await client.call_agent(self.writ_url, "write", {
                            "section": sec,
                            "description": description,
                            "donor_context": ret,
                            "critique": critique
                        })
                    except A2AError as e:
                        self.logger.error(f"Writer agent failed: {e}")
                        raise
                    
                    # Review draft
                    try:
                        review = await client.call_agent(self.rev_url, "review", {
                            "draft": draft
                        })
                    except A2AError as e:
                        self.logger.error(f"Reviewer agent failed: {e}")
                        raise
                    
                    score = review.get('score', 0)
                    self.logger.info(f"Section '{sec}' revision {revision + 1}: score={score}")
                    
                    if score >= self.min_score:
                        final_doc[sec] = draft.get('text', draft)
                        break
                    
                    critique = review.get('feedback', '')
                else:
                    # Use last draft if max revisions reached
                    final_doc[sec] = draft.get('text', draft)
                    self.logger.warning(f"Section '{sec}' did not reach min score after {self.max_revisions} revisions")
            
            self.logger.info(f"Document generation complete: {len(final_doc)} sections")
            
            # Build base response
            response = {
                "document": final_doc,
                "donor_pattern": donor_id,
                "diagram_description": description,
                "sections_generated": len(final_doc)
            }
            
            # Step 4: Publish to SharePoint (if enabled)
            if should_publish and self.sp_publisher:
                self.logger.info("Step 4: Publishing to SharePoint...")
                try:
                    publish_result = await self.sp_publisher.publish_document(
                        title=title,
                        sections=final_doc,
                        description=f"Auto-generated architecture documentation for {title}",
                        diagram_description=description,
                        donor_pattern=donor_id
                    )
                    
                    response["sharepoint"] = {
                        "published": publish_result.success,
                        "page_url": publish_result.page_url,
                        "page_id": publish_result.page_id,
                        "publish_time_ms": publish_result.publish_time_ms
                    }
                    
                    if publish_result.success:
                        self.logger.info(f"Published to SharePoint: {publish_result.page_url}")
                    else:
                        self.logger.error(f"SharePoint publish failed: {publish_result.error}")
                        response["sharepoint"]["error"] = publish_result.error
                        
                except Exception as e:
                    self.logger.error(f"SharePoint publishing error: {e}")
                    response["sharepoint"] = {
                        "published": False,
                        "error": str(e)
                    }
            
            return response

    def get_supported_tasks(self):
        return ["generate", "process", "create_document", "generate_and_publish"]

    def get_description(self):
        return "Orchestrates the document generation pipeline using Vision, Retrieval, Writer, and Reviewer agents with optional SharePoint publishing"


async def main():
    """Main entry point"""
    config = Config.get_agent_config("orchestrator")
    setup_logging(config["log_level"])
    
    agent = Orchestrator(port=config["port"], config=config)
    await agent.start()
    await agent.run_async(port=config["port"])


if __name__ == "__main__":
    asyncio.run(main())