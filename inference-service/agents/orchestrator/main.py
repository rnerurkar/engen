import sys
import os
import asyncio
import base64
import json

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/orchestrator
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service
codebase_root = os.path.dirname(inference_service_root) # .../codebase



# 2. Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import ADKAgent, AgentRequest, AgentResponse, TaskStatus
from lib.a2a_client import A2AClient, A2AError
from lib.sharepoint_publisher import SharePointPublisher, SharePointPageConfig
from config import Config

class OrchestratorAgent(ADKAgent):
    """
    Orchestrates the workflow: Retrieve -> Generate -> Review -> (Loop) -> Publish.
    Implements the 'LoopAgent' pattern.
    """
    def __init__(self):
        super().__init__(name="OrchestratorAgent", port=Config.ORCHESTRATOR_PORT)
        
        # A2A Client
        self.client = A2AClient(agent_name=self.name)
        
        # SharePoint Publisher
        sp_config = SharePointPageConfig.from_env()
        self.publisher = SharePointPublisher(sp_config) if sp_config.is_valid() else None
        if not self.publisher:
            self.logger.warning("SharePoint Publisher NOT configured. Publishing will be skipped.")

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")
        
        if req.task == "start_workflow":
            try:
                result = await self.run_workflow_loop(req.payload)
                return AgentResponse(
                    status=TaskStatus.COMPLETED,
                    result=result,
                    agent_name=self.name
                )
            except Exception as e:
                self.logger.error(f"Workflow failed: {e}", exc_info=True)
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=str(e),
                    agent_name=self.name
                )
        
        return AgentResponse(status=TaskStatus.FAILED, error=f"Unknown task: {req.task}", agent_name=self.name)

    async def run_workflow_loop(self, payload):
        """
        Executes the agent loop.
        """
        title = payload.get("title")
        image_b64 = payload.get("image_base64")
        
        if not title or not image_b64:
            raise ValueError("Missing title or image_base64")

        # 0. ANALYZE (New Step)
        self.logger.info("--- Step 0: ANALYZING Diagram (Description) ---")
        desc_resp = await self.client.call_agent(
            Config.GENERATOR_URL,
            "describe_image",
            {"image_base64": image_b64}
        )
        description = desc_resp.get("result", {}).get("description", "")
        self.logger.info(f"Generated Description: {description[:50]}...")

        # 1. RETRIEVE (Once)
        self.logger.info("--- Step 1: RETRIEVING Donor Pattern ---")
        retrieve_resp = await self.client.call_agent(
            Config.RETRIEVER_URL,
            "retrieve_donor",
            {"title": title, "description": description}
        )
        donor_context = retrieve_resp.get("result")
        if not donor_context:
            raise ValueError("Failed to retrieve donor pattern")
        
        self.logger.info(f"Donated Pattern: {donor_context.get('id')}")

        # Loop Control
        max_iterations = 3
        current_iteration = 0
        approved = False
        generated_sections = None
        critique_feedback = None

        while current_iteration < max_iterations and not approved:
            current_iteration += 1
            self.logger.info(f"--- Iteration {current_iteration}/{max_iterations} ---")
            
            # 2. GENERATE
            self.logger.info("--- Step 2: GENERATING Pattern ---")
            # Enhance context with critique if available
            # (Note: Current Generator handles one-shot, but we could inject critique into prompt if we modified Generator.
            #  For now, we just regenerating. In a full implementation, we'd pass 'critique' to Generator)
            
            # Assuming Generator is stateless one-shot for now as per previous design.
            # To support loop improvement, we would ideally pass previous attempt + critique.
            # For this 'One-Shot' implementation requested previously, we will just run generation once 
            # OR if we want to simulate the loop, we re-generate.
            # But without passing critique, re-generation is idempotent (pointless).
            # I will invoke the Generator.
            
            gen_payload = {
                "image_base64": image_b64,
                "donor_context": donor_context,
                "title": title
            }
            # If we have critique, add it to payload so Generator can improve
            if critique_feedback:
                 critique_text = critique_feedback.get("critique")
                 self.logger.info(f"Regenerating with feedback: {critique_text[:50]}...")
                 gen_payload["critique"] = critique_text

            gen_resp = await self.client.call_agent(
                 Config.GENERATOR_URL,
                 "generate_pattern",
                 gen_payload
            )
            result = gen_resp.get("result")
            generated_sections = result.get("sections")

            # 3. REVIEW (Critique)
            self.logger.info("--- Step 3: REVIEWING Content ---")
            review_resp = await self.client.call_agent(
                Config.REVIEWER_URL,
                "review_pattern",
                {"sections": generated_sections, "donor_context": donor_context}
            )
            critique_feedback = review_resp.get("result", {})
            
            approved = critique_feedback.get("approved", False)
            score = critique_feedback.get("score", 0)
            self.logger.info(f"Review Score: {score}, Approved: {approved}")
            
            if approved:
                self.logger.info("Pattern APPROVED by Reviewer.")
                break
            else:
                self.logger.warning(f"Pattern REJECTED. Issues: {critique_feedback.get('critique')}")
                # In a real loop, we'd feed this back to generator.
                # Since generator is one-shot, we might stop or retry.
                # For this demo, we break to avoid infinite loops if generator isn't improving.
                # Or we continue if we think randomness helps.
                if current_iteration == max_iterations:
                    self.logger.warning("Max iterations reached. Proceeding with best effort.")

        # 4. PUBLISH
        if self.publisher and generated_sections:
            self.logger.info("--- Step 4: PUBLISHING to SharePoint ---")
            pub_result = await self.publisher.publish_document(
                title=title,
                sections=generated_sections,
                description=f"AI Generated pattern based on {donor_context.get('title')}",
                donor_pattern=donor_context.get('id'),
                diagram_description="Processed by Gemini 1.5 Pro Multimodal"
            )
            
            if pub_result.success:
                return {
                    "status": "published",
                    "url": pub_result.page_url,
                    "iterations": current_iteration,
                    "final_score": critique_feedback.get("score")
                }
            else:
                raise RuntimeError(f"Publishing failed: {pub_result.error}")
        else:
            return {
                "status": "dry_run_completed",
                "sections": generated_sections,
                "iterations": current_iteration
            }

if __name__ == "__main__":
    agent = OrchestratorAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.ORCHESTRATOR_PORT)
