"""
Example: Updated Orchestrator Implementation
Demonstrates proper use of A2A communication library
"""

import asyncio
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib import (
    ADKAgent,
    AgentRequest,
    A2AClient,
    AgentTimeoutError,
    AgentNotAvailableError,
    A2AError,
    setup_logging
)
from typing import List, Dict, Any


class Orchestrator(ADKAgent):
    """
    Enhanced Orchestrator using A2A communication library
    Coordinates multi-agent workflow for documentation generation
    """
    
    def __init__(
        self,
        vision_url: str,
        retrieval_url: str,
        writer_url: str,
        reviewer_url: str
    ):
        super().__init__(
            name="Orchestrator",
            port=8080,
            version="2.0.0"
        )
        self.vision_url = vision_url
        self.retrieval_url = retrieval_url
        self.writer_url = writer_url
        self.reviewer_url = reviewer_url
        
        # A2A client will be created per-request
        self.max_review_iterations = 3
        self.target_review_score = 90
    
    async def initialize(self):
        """Verify all downstream agents are available"""
        self.logger.info("Checking health of downstream agents...")
        
        agent_urls = {
            "Vision": self.vision_url,
            "Retrieval": self.retrieval_url,
            "Writer": self.writer_url,
            "Reviewer": self.reviewer_url
        }
        
        async with A2AClient(self.name) as client:
            for agent_name, url in agent_urls.items():
                try:
                    health = await client.check_health(url)
                    if health.get("status") == "healthy":
                        self.logger.info(f"✓ {agent_name} agent is healthy")
                    else:
                        self.logger.warning(f"⚠ {agent_name} agent health check failed: {health}")
                except Exception as e:
                    self.logger.error(f"✗ Cannot reach {agent_name} agent at {url}: {e}")
        
        self.logger.info("Orchestrator initialization complete")
    
    def get_supported_tasks(self) -> List[str]:
        """Declare supported orchestration tasks"""
        return [
            "generate_documentation",
            "analyze_and_document",
            "full_workflow"
        ]
    
    def get_description(self) -> str:
        """Provide orchestrator description"""
        return (
            "Orchestrator coordinates multi-agent workflows for automated "
            "architecture documentation generation from diagrams."
        )
    
    async def process(self, req: AgentRequest) -> Dict[str, Any]:
        """
        Main orchestration logic
        
        Expected payload:
        {
            "image_uri": "gs://bucket/diagram.png",
            "sections": ["Problem", "Solution"],  # optional
            "quality_threshold": 90  # optional
        }
        """
        image_uri = req.payload.get('image_uri')
        sections_to_generate = req.payload.get('sections', ['Problem', 'Solution'])
        quality_threshold = req.payload.get('quality_threshold', self.target_review_score)
        
        self.logger.info(
            f"Starting documentation workflow for {len(sections_to_generate)} sections"
        )
        
        # Use A2A client for all agent communication
        async with A2AClient(self.name, default_timeout=60) as client:
            
            # Step 1: Vision Analysis
            self.logger.info("Step 1: Analyzing diagram with Vision Agent...")
            try:
                vision_result = await client.call_agent(
                    agent_url=self.vision_url,
                    task="analyze_diagram",
                    payload={"image_uri": image_uri},
                    timeout=45,
                    request_id=req.request_id
                )
                self.logger.info("Vision analysis complete")
            except AgentTimeoutError:
                raise A2AError("Vision analysis timed out")
            except AgentNotAvailableError:
                raise A2AError("Vision agent is not available")
            
            description = vision_result.get('description', '')
            
            # Step 2: Retrieval of Donor Patterns
            self.logger.info("Step 2: Retrieving similar patterns with Retrieval Agent...")
            try:
                retrieval_result = await client.call_agent(
                    agent_url=self.retrieval_url,
                    task="find_donor",
                    payload={"description": description},
                    timeout=30,
                    request_id=req.request_id
                )
                self.logger.info(f"Found donor pattern: {retrieval_result.get('donor_id')}")
            except Exception as e:
                self.logger.error(f"Retrieval failed: {e}, continuing with empty context")
                retrieval_result = {"donor_id": None, "sections": {}}
            
            # Step 3: Iterative Writing & Review for Each Section
            final_document = {}
            
            for section in sections_to_generate:
                self.logger.info(f"Step 3.{section}: Generating '{section}' section...")
                
                section_result = await self._generate_section_with_review(
                    client=client,
                    section=section,
                    description=description,
                    donor_context=retrieval_result,
                    quality_threshold=quality_threshold,
                    request_id=req.request_id
                )
                
                final_document[section] = section_result
            
            # Return complete document
            self.logger.info("Documentation workflow complete!")
            return {
                "status": "completed",
                "document": final_document,
                "vision_analysis": vision_result,
                "donor_pattern": retrieval_result.get('donor_id'),
                "sections_generated": len(final_document)
            }
    
    async def _generate_section_with_review(
        self,
        client: A2AClient,
        section: str,
        description: str,
        donor_context: Dict[str, Any],
        quality_threshold: int,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Generate a single section with iterative review and refinement
        """
        critique = ""
        best_draft = None
        best_score = 0
        
        for iteration in range(1, self.max_review_iterations + 1):
            self.logger.info(f"  Iteration {iteration}/{self.max_review_iterations}")
            
            # Generate draft
            try:
                draft_result = await client.call_agent(
                    agent_url=self.writer_url,
                    task="write_section",
                    payload={
                        "section": section,
                        "description": description,
                        "donor_context": donor_context,
                        "critique": critique
                    },
                    timeout=90,
                    request_id=f"{request_id}-{section}-draft-{iteration}"
                )
                draft_text = draft_result.get('text', '')
                self.logger.info(f"  Generated draft: {len(draft_text)} characters")
            except Exception as e:
                self.logger.error(f"  Draft generation failed: {e}")
                if best_draft:
                    return best_draft
                raise
            
            # Review draft
            try:
                review_result = await client.call_agent(
                    agent_url=self.reviewer_url,
                    task="review_draft",
                    payload={
                        "draft": draft_text,
                        "section": section
                    },
                    timeout=45,
                    request_id=f"{request_id}-{section}-review-{iteration}"
                )
                score = review_result.get('overall_score', 0)
                feedback = review_result.get('detailed_feedback', '')
                
                self.logger.info(f"  Review score: {score}/100")
                
                # Track best draft
                if score > best_score:
                    best_score = score
                    best_draft = {
                        "text": draft_text,
                        "score": score,
                        "iteration": iteration,
                        "review": review_result
                    }
                
                # Check if quality threshold met
                if score >= quality_threshold:
                    self.logger.info(f"  ✓ Quality threshold met ({score} >= {quality_threshold})")
                    return best_draft
                
                # Prepare critique for next iteration
                improvements = review_result.get('improvements_needed', [])
                if improvements:
                    critique = "Address these issues:\n" + "\n".join([
                        f"- {imp.get('issue')}: {imp.get('suggestion')}"
                        for imp in improvements[:5]  # Top 5 issues
                    ])
                else:
                    critique = feedback
                
                self.logger.info(f"  Refining based on feedback...")
                
            except Exception as e:
                self.logger.error(f"  Review failed: {e}")
                if best_draft:
                    return best_draft
                # Return draft without review
                return {
                    "text": draft_text,
                    "score": 0,
                    "iteration": iteration,
                    "review": None
                }
        
        # Max iterations reached, return best attempt
        self.logger.warning(
            f"  Max iterations reached. Best score: {best_score}/{quality_threshold}"
        )
        return best_draft or {
            "text": "",
            "score": 0,
            "iteration": 0,
            "review": None,
            "error": "Failed to generate acceptable content"
        }


async def main():
    """
    Main entry point
    """
    setup_logging(level="INFO")
    
    # Get agent URLs from environment or use defaults
    import os
    
    orchestrator = Orchestrator(
        vision_url=os.getenv("VISION_AGENT_URL", "http://localhost:8081"),
        retrieval_url=os.getenv("RETRIEVAL_AGENT_URL", "http://localhost:8082"),
        writer_url=os.getenv("WRITER_AGENT_URL", "http://localhost:8083"),
        reviewer_url=os.getenv("REVIEWER_AGENT_URL", "http://localhost:8084")
    )
    
    orchestrator.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    asyncio.run(main())
