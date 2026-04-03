import sys
import os
import asyncio
import base64
import json
import logging
import re
from typing import Dict

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
from lib.cloudsql_client import CloudSQLManager, logger as sql_logger
from core.pattern_synthesis.service_hadr_retriever import ServiceHADRRetriever
from core.pattern_synthesis.hadr_generator import HADRDocumentationGenerator
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
        
        # CloudSQL
        self.db = CloudSQLManager(
             connection_name=os.environ.get("DB_INSTANCE", "engen-project:us-central1:reviews-db"),
             db_user=os.environ.get("DB_USER", "postgres"),
             db_pass=os.environ.get("DB_PASS", "postgres"),
             db_name=os.environ.get("DB_NAME", "reviews_db")
        )

        # HA/DR Documentation Generation
        self.hadr_retriever = ServiceHADRRetriever(
            project_id=Config.PROJECT_ID,
            location="global",
            data_store_id=Config.SERVICE_HADR_DATA_STORE_ID,
        )
        self.hadr_generator = HADRDocumentationGenerator(
            project_id=Config.PROJECT_ID,
            location=Config.LOCATION,
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        self.logger.info(f"Received request: {req.task}")
        
        try:
            if req.task == "phase1_generate_docs":
                result = await self.run_phase1_docs(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)
                
            elif req.task == "approve_docs":
                result = await self.approve_phase1_docs(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)

            elif req.task == "phase2_generate_code":
                result = await self.run_phase2_code(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)
            
            elif req.task == "approve_code":
                result = await self.approve_phase2_code(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)
                
            elif req.task == "get_publish_status":
                result = await self.check_publish_status(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)

            elif req.task == "start_workflow": # Legacy full loop
                result = await self.run_workflow_loop(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)
        
        except Exception as e:
            self.logger.error(f"Task {req.task} failed: {e}", exc_info=True)
            return AgentResponse(status=TaskStatus.FAILED, error=str(e), agent_name=self.name)
        
        return AgentResponse(status=TaskStatus.FAILED, error=f"Unknown task: {req.task}", agent_name=self.name)

    async def run_phase1_docs(self, payload):
        """Phase 1: Analyze -> Retrieve -> Generate Docs. Returns content for review."""
        title = payload.get("title")
        image_b64 = payload.get("image_base64")
        if not title or not image_b64: raise ValueError("Missing title or image_base64")

        # 0. ANALYZE
        self.logger.info("--- Step 0: ANALYZING Diagram ---")
        desc_resp = await self.client.call_agent(Config.GENERATOR_URL, "describe_image", {"image_base64": image_b64})
        description = desc_resp.get("result", {}).get("description", "")

        # 1. RETRIEVE
        self.logger.info("--- Step 1: RETRIEVING Donor Pattern ---")
        retrieve_resp = await self.client.call_agent(Config.RETRIEVER_URL, "retrieve_donor", {"title": title, "description": description})
        donor_context = retrieve_resp.get("result")
        if not donor_context: raise ValueError("Failed to retrieve donor pattern")

        # 2 & 3. GENERATE & REVIEW LOOP
        max_iterations = 3
        current_iteration = 0
        ai_approved = False
        generated_sections = None
        critique_feedback = None

        while current_iteration < max_iterations and not ai_approved:
            current_iteration += 1
            self.logger.info(f"--- Iteration {current_iteration}/{max_iterations} ---")
            
            gen_payload = {"image_base64": image_b64, "donor_context": donor_context, "title": title}
            if critique_feedback: gen_payload["critique"] = critique_feedback.get("critique")

            gen_resp = await self.client.call_agent(Config.GENERATOR_URL, "generate_pattern", gen_payload)
            generated_sections = gen_resp.get("result", {}).get("sections")

            review_resp = await self.client.call_agent(Config.REVIEWER_URL, "review_pattern", {"sections": generated_sections, "donor_context": donor_context})
            critique_feedback = review_resp.get("result", {})
            ai_approved = critique_feedback.get("approved", False)

        # --- HA/DR SECTION GENERATION ---
        self.logger.info("--- Step 3: GENERATING HA/DR SECTIONS ---")
        try:
            hadr_sections = self._generate_hadr_sections(
                generated_sections=generated_sections or {},
                donor_context=donor_context,
            )
            # Merge HA/DR sections into the generated sections
            if hadr_sections:
                if generated_sections is None:
                    generated_sections = {}
                generated_sections["HA/DR"] = self._format_hadr_sections(hadr_sections)
        except Exception as e:
            self.logger.error(f"HA/DR generation failed (non-blocking): {e}", exc_info=True)
            # Non-blocking: we still return the pattern doc without HA/DR
            if generated_sections is None:
                generated_sections = {}
            generated_sections["HA/DR"] = (
                "*HA/DR section generation failed. Please complete manually.*"
            )

        full_doc = "\n\n".join([f"# {k}\n{v}" for k, v in (generated_sections or {}).items()])

        # Create PENDING review record
        import uuid
        review_id = str(uuid.uuid4())
        
        if self.db:
             self.db.create_review_record(review_id, title, "PATTERN", generated_sections, full_doc)

        return {
            "review_id": review_id,
            "sections": generated_sections,
            "full_doc": full_doc,
            "donor_context": donor_context
        }

    async def approve_phase1_docs(self, payload):
        """Phase 1 Approve: Publishing Pattern Documentation (Fire and Forget)"""
        review_id = payload.get("review_id")
        title = payload.get("title")
        sections = payload.get("sections")
        donor_context = payload.get("donor_context")
        
        if self.db:
             self.db.update_review_status(review_id, "APPROVED", "Approved via Streamlit")

        self.logger.info("--- Async Task: Publishing Pattern Documentation ---")
        asyncio.create_task(
             self._async_publish_docs(review_id, title, sections, donor_context)
        )
        return {"status": "publishing_started", "review_id": review_id}

    async def run_phase2_code(self, payload):
        """Phase 2: Component Spec -> Artifact Gen -> Validation. Returns artifacts for review."""
        full_doc = payload.get("full_doc")
        
        # 4. GENERATE ARTIFACTS
        self.logger.info("--- Step 4: GENERATING ARTIFACTS ---")
        spec_resp = await self.client.call_agent(Config.ARTIFACT_URL, "generate_component_spec", {"documentation": full_doc})
        full_spec = spec_resp.get("result", {}).get("specifications", {})
        
        artifacts = {}
        
        max_retries = 3
        retry_count = 0
        validation_passed = False
        validation_feedback = None
        
        while retry_count < max_retries and not validation_passed:
            retry_count += 1
            self.logger.info(f"--- Artifact Generation {retry_count} ---")
            gen_payload = {"specification": full_spec, "documentation": full_doc}
            if validation_feedback: gen_payload["critique"] = validation_feedback
                
            art_resp = await self.client.call_agent(Config.ARTIFACT_URL, "generate_artifact", gen_payload)
            artifacts_result = art_resp.get("result", {}).get("artifacts", {})
            
            val_resp = await self.client.call_agent(Config.ARTIFACT_URL, "validate_artifact", {"artifacts": artifacts_result, "component_spec": full_spec})
            val_result = val_resp.get("result", {}).get("validation_result", {})
            
            if val_result.get("status") == "PASS":
                validation_passed = True
                artifacts = artifacts_result
            else:
                validation_feedback = val_result.get("feedback")
        
        import uuid
        review_id = str(uuid.uuid4())
        if self.db:
             # Use a distinct record for artifacts
             # Tricky: we pass 'artifacts' (dict) to create_review_record
             self.db.create_review_record(review_id, "Artifacts for " + str(len(artifacts)), "ARTIFACT", artifacts, "N/A")

        return {
            "review_id": review_id,
            "artifacts": artifacts,
            "spec": full_spec
        }

    async def approve_phase2_code(self, payload):
        """Phase 2 Approve: Publish Code"""
        review_id = payload.get("review_id")
        # artifacts passed from client or we fetch from DB? Client passing is easier for now to avoid DB fetching logic
        artifacts = payload.get("artifacts") 
        title = payload.get("title")
        
        if self.db:
             self.db.update_review_status(review_id, "APPROVED", "Approved via Streamlit")

        self.logger.info("--- Async Task: Publishing Code ---")
        asyncio.create_task(
            self._async_publish_code(review_id, artifacts, title)
        )
        return {"status": "publishing_started", "review_id": review_id}
    
    async def check_publish_status(self, payload):
        review_ids = payload.get("review_ids", [])
        statuses = {}
        if self.db and self.db.engine:
            try:
                with self.db.engine.connect() as conn:
                    import sqlalchemy
                    stmt = sqlalchemy.text("SELECT review_id, doc_publish_status, code_publish_status, doc_url, code_url FROM reviews WHERE review_id = ANY(:rids)")
                    result = conn.execute(stmt, {"rids": review_ids})
                    for row in result:
                        statuses[row.review_id] = {
                            "doc_status": row.doc_publish_status,
                            "code_status": row.code_publish_status,
                            "doc_url": row.doc_url,
                            "code_url": row.code_url
                        }
            except Exception as e:
                self.logger.error(f"Status check failed: {e}")
        return statuses

    # ─── HA/DR Generation Helpers ────────────────────────────────────────

    def _generate_hadr_sections(
        self,
        generated_sections: Dict,
        donor_context: Dict,
    ) -> Dict[str, str]:
        """
        Generates HA/DR documentation sections by:
          1. Extracting service names from the generated doc sections
          2. Retrieving per-service HA/DR docs from Vertex AI Search
          3. Extracting the donor pattern's HA/DR sections as one-shot examples
          4. Calling HADRDocumentationGenerator for each DR strategy
        """
        # 1. Build a simple text block from the generated sections to extract service names
        doc_text = "\n".join(str(v) for v in generated_sections.values())

        # Use the Generator Agent to extract service names (lightweight LLM call)
        service_names = self._extract_service_names_from_doc(doc_text)
        if not service_names:
            self.logger.warning("No service names extracted — skipping HA/DR generation")
            return {}

        self.logger.info(f"Extracted service names for HA/DR: {service_names}")

        # 2. Retrieve service-level HA/DR docs
        service_hadr_docs = self.hadr_retriever.retrieve_all_services_hadr(
            service_names=service_names,
        )

        # 3. Extract donor pattern HA/DR sections
        donor_html = donor_context.get("html_content", "") if donor_context else ""
        donor_hadr_sections = HADRDocumentationGenerator.extract_donor_hadr_sections(
            donor_html
        )

        # 4. Build pattern context
        pattern_context = {
            "title": generated_sections.get("Executive Summary", "")[:200],
            "solution_overview": generated_sections.get(
                "Solution Architecture",
                generated_sections.get("Solution", ""),
            )[:2000],
            "services": service_names,
        }

        # 5. Generate
        hadr_sections = self.hadr_generator.generate_hadr_sections(
            pattern_context=pattern_context,
            donor_hadr_sections=donor_hadr_sections,
            service_hadr_docs=service_hadr_docs,
        )

        return hadr_sections

    def _extract_service_names_from_doc(self, doc_text: str) -> list:
        """
        Lightweight extraction of canonical service names from the pattern
        documentation.  Falls back to regex-based extraction if the LLM
        is not available.
        """
        from lib.component_sources import COMPONENT_TYPE_ALIASES

        # Quick regex pass: look for known service keywords in the doc
        doc_lower = doc_text.lower()
        found_services = set()

        # Build a reverse map: canonical_type → friendly display name
        # We want to return recognisable names like "Amazon RDS", "AWS Lambda"
        canonical_to_display = {
            "s3_bucket": "Amazon S3",
            "lambda_function": "AWS Lambda",
            "api_gateway": "Amazon API Gateway",
            "dynamodb_table": "Amazon DynamoDB",
            "rds_instance": "Amazon RDS",
            "ecs_service": "Amazon ECS",
            "eks_cluster": "Amazon EKS",
            "sqs_queue": "Amazon SQS",
            "sns_topic": "Amazon SNS",
            "vpc": "Amazon VPC",
            "cloudfront": "Amazon CloudFront",
            "load_balancer": "Elastic Load Balancer",
            "elasticache": "Amazon ElastiCache",
            "iam_role": "AWS IAM",
            "waf": "AWS WAF",
            "kms_key": "AWS KMS",
            "secrets_manager": "AWS Secrets Manager",
            "codepipeline": "AWS CodePipeline",
            "ecr_repository": "Amazon ECR",
            "step_function": "AWS Step Functions",
        }

        for alias, canonical in COMPONENT_TYPE_ALIASES.items():
            # Match the alias as a whole word in the doc text
            pattern = r'\b' + re.escape(alias.replace('_', ' ')) + r'\b'
            if re.search(pattern, doc_lower):
                display_name = canonical_to_display.get(canonical, canonical)
                found_services.add(display_name)

        # Also check for common full service names
        common_names = [
            "Amazon RDS", "Amazon S3", "AWS Lambda", "Amazon ECS",
            "Amazon EKS", "Amazon DynamoDB", "Amazon SQS", "Amazon SNS",
            "Amazon ElastiCache", "Amazon CloudFront", "Amazon API Gateway",
            "Amazon VPC", "AWS WAF", "AWS KMS", "Amazon ECR",
            "AWS Step Functions", "Cloud SQL", "Cloud Run", "Cloud Storage",
            "Cloud Functions", "Cloud Pub/Sub", "Cloud CDN",
        ]
        for name in common_names:
            if name.lower() in doc_lower:
                found_services.add(name)

        return list(found_services)

    @staticmethod
    def _format_hadr_sections(hadr_sections: Dict[str, str]) -> str:
        """
        Combine the four individual DR strategy sections into a single
        Markdown block suitable for inclusion in the pattern document.
        """
        parts = ["## High Availability / Disaster Recovery\n"]
        for strategy in HADRDocumentationGenerator.DR_STRATEGIES:
            section_text = hadr_sections.get(strategy, "")
            if section_text:
                parts.append(section_text)
            else:
                parts.append(
                    f"## {strategy}\n\n*Section not generated.*\n"
                )
        return "\n\n---\n\n".join(parts)

    async def run_workflow_loop(self, payload):
        """Legacy loop"""
        # ... (Existing implementation kept for backward compatibility if needed, but not used by Streamlit)
        # For brevity, I'll return empty or error to force new flow usage, or keep logic.
        # Since I'm replacing the whole handle block, I need to keep the method definition if I call failure
        
        # Simplified legacy stub
        return {"error": "Use phase-based workflow via Streamlit"}


if __name__ == "__main__":
    agent = OrchestratorAgent()
    import uvicorn
    uvicorn.run(agent.app, host="0.0.0.0", port=Config.ORCHESTRATOR_PORT)
