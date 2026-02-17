import sys
import os
import asyncio
import base64
import json
import logging

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
from lib.github_publisher import GitHubMCPPublisher
from config import Config

class OrchestratorAgent(ADKAgent):
    """
    Orchestrates the workflow: Retrieve -> Generate -> Review -> (Human Check) -> Artifacts -> (Human Check) -> Publish.
    """
    def __init__(self):
        super().__init__(name="OrchestratorAgent", port=Config.ORCHESTRATOR_PORT)
        
        # A2A Client
        self.client = A2AClient(agent_name=self.name)
        
        # SharePoint Publisher
        sp_config = SharePointPageConfig.from_env()
        self.publisher = SharePointPublisher(sp_config) if sp_config.is_valid() else None
        if not self.publisher:
            self.logger.warning("SharePoint Publisher NOT configured. Documentation publishing will be skipped.")
            
        # GitHub Publisher (Defaults to environment variables)
        self.gh_owner = os.environ.get("GITHUB_OWNER", "rnerurkar")
        self.gh_repo = os.environ.get("GITHUB_REPO", "engen")
        self.gh_branch = os.environ.get("GITHUB_BRANCH", "main")
        self.code_publisher = GitHubMCPPublisher(owner=self.gh_owner, repo=self.gh_repo, branch=self.gh_branch)

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

    async def request_human_verification(self, title: str, stage: str, content: dict, documentation: str) -> bool:
        """
        Helper to call the Human Verifier Agent.
        Returns True if APPROVED, False otherwise.
        """
        self.logger.info(f"--- Requesting Human Verification for {stage} ---")
        try:
            # Prepare payload for verifier
            payload = {
                "title": title,
                "stage": stage,
                "artifacts": content,
                "documentation": documentation
            }
            
            verify_resp = await self.client.call_agent(
                Config.VERIFIER_URL,
                "request_human_review",
                payload
            )
            
            result = verify_resp.get("result", {})
            status = result.get("status")
            self.logger.info(f"Human Review Status for {stage}: {status}")
            
            if status == "APPROVED":
                return True
            else:
                self.logger.warning(f"Project was not approved at {stage}. Status: {status}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed during Human Verification ({stage}): {e}")
            return False


    async def run_workflow_loop(self, payload):
        """
        Executes the agent loop.
        """
        title = payload.get("title")
        image_b64 = payload.get("image_base64")
        
        if not title or not image_b64:
            raise ValueError("Missing title or image_base64")

        # 0. ANALYZE
        self.logger.info("--- Step 0: ANALYZING Diagram ---")
        desc_resp = await self.client.call_agent(
            Config.GENERATOR_URL,
            "describe_image",
            {"image_base64": image_b64}
        )
        description = desc_resp.get("result", {}).get("description", "")

        # 1. RETRIEVE
        self.logger.info("--- Step 1: RETRIEVING Donor Pattern ---")
        retrieve_resp = await self.client.call_agent(
            Config.RETRIEVER_URL,
            "retrieve_donor",
            {"title": title, "description": description}
        )
        donor_context = retrieve_resp.get("result")
        if not donor_context:
            raise ValueError("Failed to retrieve donor pattern")

        # 2 & 3. GENERATE & REVIEW LOOP
        max_iterations = 3
        current_iteration = 0
        ai_approved = False
        generated_sections = None
        critique_feedback = None

        while current_iteration < max_iterations and not ai_approved:
            current_iteration += 1
            self.logger.info(f"--- Iteration {current_iteration}/{max_iterations} ---")
            
            # Generate Pattern
            gen_payload = {
                "image_base64": image_b64,
                "donor_context": donor_context,
                "title": title
            }
            if critique_feedback:
                 gen_payload["critique"] = critique_feedback.get("critique")

            gen_resp = await self.client.call_agent(
                 Config.GENERATOR_URL,
                 "generate_pattern",
                 gen_payload
            )
            generated_sections = gen_resp.get("result", {}).get("sections")

            # Review Pattern (AI)
            review_resp = await self.client.call_agent(
                Config.REVIEWER_URL,
                "review_pattern",
                {"sections": generated_sections, "donor_context": donor_context}
            )
            critique_feedback = review_resp.get("result", {})
            ai_approved = critique_feedback.get("approved", False)
            
            if ai_approved:
                self.logger.info("Pattern APPROVED by AI Reviewer.")
            else:
                self.logger.warning(f"Pattern REJECTED by AI. Critique: {critique_feedback.get('critique')[:100]}...")

        # Construct full documentation string
        full_doc = "\n\n".join([f"# {k}\n{v}" for k, v in (generated_sections or {}).items()])

        # 3.5 HUMAN VERIFICATION (PATTERN)
        # Even if AI rejected (and we ran out of retries), we might want human final say or abort.
        # Here we only proceed if we have *some* content.
        if not generated_sections:
            raise RuntimeError("Failed to generate any pattern sections.")

        human_pattern_approved = await self.request_human_verification(
            title=title, 
            stage="PATTERN", 
            content=generated_sections, 
            documentation=full_doc
        )

        if not human_pattern_approved:
            return {"status": "rejected_by_human_pattern", "reason": "Human verification failed at Pattern stage."}


        # 4. GENERATE ARTIFACTS
        self.logger.info("--- Step 4: GENERATING ARTIFACTS ---")
        artifacts = []
        try:
            # 4a. Component Specification Extraction
            spec_resp = await self.client.call_agent(
                Config.ARTIFACT_URL,
                "generate_component_spec",
                {"documentation": full_doc}
            )
            
            if spec_resp.get("status") == "completed":
                spec_result = spec_resp.get("result", {})
                full_spec = spec_result.get("specifications", {}) # Comprehensive Spec
                
                # 4b. Generate Artifacts Loop (Generate -> Validate -> Retry)
                max_retries = 3
                retry_count = 0
                validation_passed = False
                validation_feedback = None
                
                while retry_count < max_retries and not validation_passed:
                    retry_count += 1
                    self.logger.info(f"--- Artifact Generation Attempt {retry_count}/{max_retries} ---")
                    
                    # Generate full set of artifacts
                    gen_payload = {
                        "specification": full_spec,
                        "documentation": full_doc
                    }
                    if validation_feedback:
                        gen_payload["critique"] = validation_feedback
                        
                    art_resp = await self.client.call_agent(
                        Config.ARTIFACT_URL,
                        "generate_artifact",
                        gen_payload
                    )
                    
                    if art_resp.get("status") == "completed":
                        artifacts_result = art_resp.get("result", {}).get("artifacts", {})
                        
                        # Validate the generated artifacts
                        val_resp = await self.client.call_agent(
                            Config.ARTIFACT_URL,
                            "validate_artifact",
                            {
                                "artifacts": artifacts_result,
                                "component_spec": full_spec
                            }
                        )
                        
                        if val_resp.get("status") == "completed":
                            val_result = val_resp.get("result", {}).get("validation_result", {})
                            if val_result.get("status") == "PASS":
                                validation_passed = True
                                artifacts = artifacts_result # Keep the valid artifacts
                                self.logger.info("Artifacts passed validation.")
                            else:
                                validation_feedback = val_result.get("feedback")
                                issues = val_result.get("issues", [])
                                self.logger.warning(f"Artifact validation failed. Issues: {len(issues)}. Retrying...")
                        else:
                             self.logger.error("Validation agent failed execution.")
                    else:
                        self.logger.error("Artifact generation step failed.")
                
                if not validation_passed:
                    self.logger.warning("Artifact generation exceeded max retries without passing validation.")
            else:
                 self.logger.error("Failed component spec generation.")
                 self.logger.error("Failed component spec generation.")

        except Exception as e:
            self.logger.error(f"Error during artifact generation: {e}", exc_info=True)

        # 5. HUMAN VERIFICATION (ARTIFACTS)
        human_artifacts_approved = False
        if artifacts:
            human_artifacts_approved = await self.request_human_verification(
                title=title,
                stage="ARTIFACT", 
                content={"count": len(artifacts), "items": artifacts},
                documentation="Please review the attached Terraform JSON artifacts."
            )
        else:
            self.logger.warning("No artifacts generated to verify.")

        if not human_artifacts_approved:
             return {"status": "rejected_by_human_artifacts", "reason": "Human verification failed at Artifact stage."}

        # 6. PUBLISH
        if human_artifacts_approved:
            self.logger.info("--- Step 6: PUBLISHING ---")
            
            # 6a. Publish Documentation to SharePoint (Optional)
            sharepoint_url = "skipped"
            if self.publisher:
                self.logger.info("Publishing Documentation to SharePoint...")
                 # Format artifacts for appending to the page (just as a reference)
                artifact_section = "\n## Generated Infrastructure\n"
                
                # Handle IaC Templates
                iac = artifacts.get("iac_templates", {})
                for iac_type, files in iac.items():
                    artifact_section += f"### {iac_type.upper()} Templates\n"
                    for filename, content in files.items():
                        artifact_section += f"#### {filename}\n```hcl\n{content}\n```\n"

                # Handle Boilerplate
                boilerplate = artifacts.get("boilerplate_code", {})
                if boilerplate:
                    artifact_section += "\n## Reference Implementation (Boilerplate)\n"
                    for comp_id, details in boilerplate.items():
                        artifact_section += f"### Component: {comp_id}\n"
                        files = details.get("files", {})
                        for fname, fcontent in files.items():
                            lang = "python" if fname.endswith(".py") else "bash"
                            artifact_section += f"#### {fname}\n```{lang}\n{fcontent}\n```\n"
                
                # Add to sections
                generated_sections["Infrastructure"] = artifact_section

                pub_result = await self.publisher.publish_document(
                    title=title,
                    sections=generated_sections,
                    description=f"AI Generated pattern based on {donor_context.get('title')}",
                    donor_pattern=donor_context.get('id'),
                    diagram_description="Processed by Gemini 1.5 Pro Multimodal"
                )
                if pub_result.success:
                    sharepoint_url = pub_result.page_url
            
            # 6b. Publish Code to GitHub
            self.logger.info("Publishing Code to GitHub...")
            gh_result = await self.code_publisher.publish_artifacts(
                artifacts=artifacts,
                message=f"feat: generated artifacts for pattern '{title}'"
            )
            
            return {
                "status": "published",
                "docs_url": sharepoint_url,
                "code_repo": f"{self.gh_owner}/{self.gh_repo}",
                "commit_info": gh_result,
                "final_score": critique_feedback.get("score")
            }
        else:
            return {
                "status": "dry_run_completed",
                "sections": generated_sections
            }

if __name__ == "__main__":
    agent = OrchestratorAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.ORCHESTRATOR_PORT)
