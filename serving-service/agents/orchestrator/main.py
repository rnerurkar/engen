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

    async def process(self, req: AgentRequest) -> dict:
        """Process architecture diagram through the agent pipeline"""
        img = req.payload.get('image') or req.payload.get('image_uri')
        if not img:
            raise ValueError("Missing 'image' or 'image_uri' in payload")
        
        self.logger.info(f"Processing diagram: {img}")
        
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
            
            return {
                "document": final_doc,
                "donor_pattern": donor_id,
                "diagram_description": description
            }

    def get_supported_tasks(self):
        return ["generate", "process", "create_document"]

    def get_description(self):
        return "Orchestrates the document generation pipeline using Vision, Retrieval, Writer, and Reviewer agents"


async def main():
    """Main entry point"""
    config = Config.get_agent_config("orchestrator")
    setup_logging(config["log_level"])
    
    agent = Orchestrator(port=config["port"], config=config)
    await agent.start()
    await agent.run_async(port=config["port"])


if __name__ == "__main__":
    asyncio.run(main())