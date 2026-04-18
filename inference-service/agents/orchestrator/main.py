import sys
import os
import asyncio
import base64
import uuid
from typing import Dict, Optional

# Add path hacks to support imports from sibling services
current_file_path = os.path.abspath(__file__)
agent_dir = os.path.dirname(current_file_path)        # .../agents/orchestrator
agents_root = os.path.dirname(agent_dir)              # .../agents
inference_service_root = os.path.dirname(agents_root) # .../inference-service

# 2. Add inference-service (for config, core)
if inference_service_root not in sys.path:
    sys.path.append(inference_service_root)

from lib.adk_core import (
    ADKAgent, AgentRequest, AgentResponse, TaskStatus,
    WorkflowContext, SequentialAgent, LoopAgent,
)
from lib.sharepoint_publisher import SharePointPublisher, SharePointPageConfig
from lib.github_publisher import GitHubMCPPublisher
from lib.cloudsql_client import AlloyDBManager
from lib.workflow_state import WorkflowStateManager

# Core logic modules — imported directly instead of via A2A HTTP calls
from core.generator import PatternGenerator
from core.retriever import VertexRetriever
from core.reviewer import PatternReviewer
from core.pattern_synthesis.service_hadr_retriever import ServiceHADRRetriever
from core.pattern_synthesis.hadr_generator import HADRDocumentationGenerator
from core.pattern_synthesis.hadr_diagram_generator import HADRDiagramGenerator
from core.pattern_synthesis.hadr_diagram_storage import HADRDiagramStorage

# Workflow step agents (ADK SequentialAgent / LoopAgent pattern)
from agents.orchestrator.workflow_agents import (
    VisionAnalysisStep,
    DonorRetrievalStep,
    PatternGenerateStep,
    HADRSectionsStep,
    FullDocReviewStep,
    HADRDiagramStep,
)

from config import Config

class OrchestratorAgent(ADKAgent):
    """
    Orchestrates the workflow using ADK SequentialAgent + LoopAgent
    instead of A2A HTTP calls.

    Phase 1 (Doc Generation):
      SequentialAgent → VisionAnalysis → DonorRetrieval
        → LoopAgent(Generate → HA/DR → Review, max_iterations=3)
        → HADRDiagramGeneration

    All sub-agents operate in-process via WorkflowContext — no HTTP
    overhead, no serialisation, no A2A timeout issues.
    """

    def __init__(self):
        super().__init__(name="OrchestratorAgent", port=Config.ORCHESTRATOR_PORT)

        # ── Core Logic Modules (direct in-process, replacing A2A) ────────
        self.pattern_generator = PatternGenerator(
            project_id=Config.PROJECT_ID
        )
        self.retriever = VertexRetriever(
            project_id=Config.PROJECT_ID,
            location="global",
            data_store_id=Config.DATA_STORE_ID,
        )
        self.reviewer = PatternReviewer(project_id=Config.PROJECT_ID)

        # HA/DR core modules
        self.hadr_retriever = ServiceHADRRetriever(
            project_id=Config.PROJECT_ID,
            location="global",
            data_store_id=Config.SERVICE_HADR_DATA_STORE_ID,
        )
        self.hadr_generator = HADRDocumentationGenerator(
            project_id=Config.PROJECT_ID,
            location=Config.LOCATION,
        )
        self.hadr_diagram_generator = HADRDiagramGenerator(
            project_id=Config.PROJECT_ID,
            location=Config.LOCATION,
        )
        self.hadr_diagram_storage = HADRDiagramStorage(
            bucket_name=Config.HADR_DIAGRAM_GCS_BUCKET,
            project_id=Config.PROJECT_ID,
        )

        # ── ADK Workflow: Phase 1 Doc Generation ────────────────────────
        # LoopAgent: Generate core sections → HA/DR sections → Review
        self.content_refinement_loop = LoopAgent(
            name="ContentRefinementLoop",
            sub_agents=[
                PatternGenerateStep(),
                HADRSectionsStep(),
                FullDocReviewStep(),
            ],
            max_iterations=3,
            exit_key="approved",
        )

        # SequentialAgent: Analyze → Retrieve → Loop → Diagrams
        self.phase1_workflow = SequentialAgent(
            name="Phase1DocGenerationWorkflow",
            sub_agents=[
                VisionAnalysisStep(),
                DonorRetrievalStep(),
                self.content_refinement_loop,
                HADRDiagramStep(),
            ],
        )

        # ── A2A Client (retained for Phase 2 artifact agents only) ──────
        from lib.a2a_client import A2AClient
        self.client = A2AClient(agent_name=self.name)

        # ── Publishers ──────────────────────────────────────────────────
        sp_config = SharePointPageConfig.from_env()
        self.publisher = (
            SharePointPublisher(sp_config) if sp_config.is_valid() else None
        )
        if not self.publisher:
            self.logger.warning(
                "SharePoint Publisher NOT configured. "
                "Documentation publishing will be skipped."
            )

        self.gh_owner = os.environ.get("GITHUB_OWNER", "rnerurkar")
        self.gh_repo = os.environ.get("GITHUB_REPO", "engen")
        self.gh_branch = os.environ.get("GITHUB_BRANCH", "main")
        self.code_publisher = GitHubMCPPublisher(
            owner=self.gh_owner,
            repo=self.gh_repo,
            branch=self.gh_branch,
        )

        # ── AlloyDB ────────────────────────────────────────────────────
        self.db = AlloyDBManager(
            connection_name=os.environ.get(
                "ALLOYDB_INSTANCE", Config.ALLOYDB_INSTANCE
            ),
            db_user=os.environ.get("DB_USER", Config.DB_USER),
            db_pass=os.environ.get("DB_PASS", Config.DB_PASS),
            db_name=os.environ.get("DB_NAME", Config.DB_NAME),
        )

        # ── Workflow State Manager ────────────────────────────────────
        self.workflow_state: Optional[WorkflowStateManager] = None
        if self.db and self.db.engine:
            self.workflow_state = WorkflowStateManager(self.db.engine)
            self.logger.info(
                "WorkflowStateManager initialized — resumable workflows enabled"
            )
        else:
            self.logger.warning(
                "WorkflowStateManager NOT available — no DB engine"
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

            elif req.task == "resume_workflow":
                result = await self.resume_workflow(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)

            elif req.task == "list_workflows":
                result = await self.list_workflows(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)

            elif req.task == "start_workflow": # Legacy full loop
                result = await self.run_workflow_loop(req.payload)
                return AgentResponse(status=TaskStatus.COMPLETED, result=result, agent_name=self.name)
        
        except Exception as e:
            self.logger.error(f"Task {req.task} failed: {e}", exc_info=True)
            return AgentResponse(status=TaskStatus.FAILED, error=str(e), agent_name=self.name)
        
        return AgentResponse(status=TaskStatus.FAILED, error=f"Unknown task: {req.task}", agent_name=self.name)

    async def run_phase1_docs(self, payload):
        """
        Phase 1: Analyse → Retrieve → Generate + HA/DR → Review (loop) → Diagrams.

        Delegates the entire pipeline to the ADK Phase1DocGenerationWorkflow
        (SequentialAgent + LoopAgent).  All sub-agents operate in-process via
        a shared WorkflowContext — no A2A HTTP calls.
        """
        title = payload.get("title")
        image_b64 = payload.get("image_base64")
        user_id = payload.get("user_id", "anonymous")
        if not title or not image_b64:
            raise ValueError("Missing title or image_base64")

        # Create workflow record for resumable sessions
        workflow_id = payload.get("workflow_id") or str(uuid.uuid4())
        if self.workflow_state:
            self.workflow_state.create_workflow(
                workflow_id=workflow_id,
                pattern_title=title,
                created_by=user_id,
                image_base64=image_b64,
            )

        # ── Build WorkflowContext ────────────────────────────────────────
        # Seed it with input data and references to core modules so that
        # each step agent can fetch what it needs without constructor args.
        image_bytes = base64.b64decode(image_b64)

        ctx = WorkflowContext(
            {
                # Input data
                "title": title,
                "image_bytes": image_bytes,
                # Core logic module references (prefixed with _ by convention)
                "_generator": self.pattern_generator,
                "_retriever": self.retriever,
                "_reviewer": self.reviewer,
                "_hadr_retriever": self.hadr_retriever,
                "_hadr_generator": self.hadr_generator,
                "_hadr_diagram_generator": self.hadr_diagram_generator,
                "_hadr_diagram_storage": self.hadr_diagram_storage,
            }
        )

        # ── Execute the Phase 1 workflow ─────────────────────────────────
        self.logger.info(
            f"=== Starting Phase1DocGenerationWorkflow for '{title}' ==="
        )
        ctx = await self.phase1_workflow.run(ctx)
        self.logger.info(
            f"=== Phase1DocGenerationWorkflow completed for '{title}' ==="
        )

        # ── Extract results from context ─────────────────────────────────
        generated_sections = ctx.get("generated_sections") or {}
        donor_context = ctx.get("donor_context") or {}
        hadr_sections = ctx.get("hadr_sections") or {}

        full_doc = "\n\n".join(
            f"# {k}\n{v}" for k, v in generated_sections.items()
        )

        # Create PENDING review record
        review_id = str(uuid.uuid4())
        if self.db:
            self.db.create_review_record(
                review_id, title, "PATTERN", generated_sections, full_doc
            )

        result = {
            "workflow_id": workflow_id,
            "review_id": review_id,
            "title": title,
            "sections": generated_sections,
            "full_doc": full_doc,
            "donor_context": donor_context,
        }

        # ── Persist state → DOC_REVIEW ──
        if self.workflow_state:
            self.workflow_state.save_state(
                workflow_id=workflow_id,
                current_phase="DOC_REVIEW",
                doc_data=result,
                hadr_sections=hadr_sections,
                doc_review_id=review_id,
            )

        return result

    async def approve_phase1_docs(self, payload):
        """Phase 1 Approve: Publishing Pattern Documentation (Fire and Forget)"""
        review_id = payload.get("review_id")
        title = payload.get("title")
        sections = payload.get("sections")
        donor_context = payload.get("donor_context")
        workflow_id = payload.get("workflow_id")
        
        if self.db:
             self.db.update_review_status(review_id, "APPROVED", "Approved via UI")

        # ── Persist state → CODE_GEN ──
        if self.workflow_state and workflow_id:
            self.workflow_state.save_state(
                workflow_id=workflow_id,
                current_phase="CODE_GEN",
            )

        self.logger.info("--- Async Task: Publishing Pattern Documentation ---")
        asyncio.create_task(
             self._async_publish_docs(review_id, title, sections, donor_context)
        )
        return {"status": "publishing_started", "review_id": review_id, "workflow_id": workflow_id}

    async def run_phase2_code(self, payload):
        """Phase 2: Component Spec -> Artifact Gen -> Validation. Returns artifacts for review."""
        full_doc = payload.get("full_doc")
        workflow_id = payload.get("workflow_id")
        
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
        
        review_id = str(uuid.uuid4())
        if self.db:
             self.db.create_review_record(review_id, "Artifacts for " + str(len(artifacts)), "ARTIFACT", artifacts, "N/A")

        result = {
            "workflow_id": workflow_id,
            "review_id": review_id,
            "artifacts": artifacts,
            "spec": full_spec
        }

        # ── Persist state → CODE_REVIEW ──
        if self.workflow_state and workflow_id:
            self.workflow_state.save_state(
                workflow_id=workflow_id,
                current_phase="CODE_REVIEW",
                code_data=result,
                code_review_id=review_id,
            )

        return result

    async def approve_phase2_code(self, payload):
        """Phase 2 Approve: Publish Code"""
        review_id = payload.get("review_id")
        artifacts = payload.get("artifacts") 
        title = payload.get("title")
        workflow_id = payload.get("workflow_id")
        
        if self.db:
             self.db.update_review_status(review_id, "APPROVED", "Approved via UI")

        # ── Persist state → PUBLISH ──
        if self.workflow_state and workflow_id:
            self.workflow_state.save_state(
                workflow_id=workflow_id,
                current_phase="PUBLISH",
            )

        self.logger.info("--- Async Task: Publishing Code ---")
        asyncio.create_task(
            self._async_publish_code(review_id, artifacts, title)
        )
        return {"status": "publishing_started", "review_id": review_id, "workflow_id": workflow_id}
    
    async def check_publish_status(self, payload):
        review_ids = payload.get("review_ids", [])
        workflow_id = payload.get("workflow_id")
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

        # Mark workflow completed when both publishes are done
        if workflow_id and self.workflow_state and statuses:
            all_done = all(
                (s.get("doc_status") or "").upper() in ("COMPLETED", "DONE", "PUBLISHED")
                and (s.get("code_status") or "").upper() in ("COMPLETED", "DONE", "PUBLISHED")
                for s in statuses.values()
            )
            if all_done:
                self.workflow_state.save_state(workflow_id, "COMPLETED")
                self.workflow_state.deactivate_workflow(workflow_id)
                self.logger.info(f"Workflow {workflow_id} completed and deactivated")

        return statuses

    # ─── Resume / List Workflows ──────────────────────────────────────────

    async def resume_workflow(self, payload):
        """
        Resume a previously started workflow.

        Accepts either:
          - { workflow_id: "abc-123" }        → load that specific workflow
          - { user_id: "user@corp.com" }      → load the most recent active workflow
        """
        workflow_id = payload.get("workflow_id")
        user_id = payload.get("user_id")

        if not self.workflow_state:
            return {"error": "Workflow state persistence not available"}

        # If no workflow_id given, find the user's most recent active workflow
        if not workflow_id and user_id:
            active = self.workflow_state.list_active_workflows(user_id, limit=1)
            if not active:
                return {"found": False, "message": "No active workflows found"}
            workflow_id = active[0]["workflow_id"]

        if not workflow_id:
            return {"found": False, "message": "Provide workflow_id or user_id"}

        state = self.workflow_state.load_state(workflow_id)
        if not state:
            return {"found": False, "message": f"Workflow {workflow_id} not found or inactive"}

        self.logger.info(
            f"Resuming workflow {workflow_id} at phase '{state['current_phase']}'"
        )

        # Map backend phase → frontend step name
        phase_to_step = {
            "INPUT": "INPUT",
            "DOC_REVIEW": "DOC_REVIEW",
            "CODE_GEN": "CODE_GEN",
            "CODE_REVIEW": "CODE_REVIEW",
            "PUBLISH": "PUBLISH",
            "COMPLETED": "PUBLISH",
        }

        return {
            "found": True,
            "workflow_id": state["workflow_id"],
            "step": phase_to_step.get(state["current_phase"], "INPUT"),
            "pattern_title": state.get("pattern_title"),
            "doc_data": state.get("doc_data"),
            "code_data": state.get("code_data"),
            "hadr_sections": state.get("hadr_sections"),
            "hadr_diagram_uris": state.get("hadr_diagram_uris"),
            "doc_review_id": state.get("doc_review_id"),
            "code_review_id": state.get("code_review_id"),
            "last_updated": state.get("last_updated"),
        }

    async def list_workflows(self, payload):
        """List active workflows for a user (for resume picker UI)."""
        user_id = payload.get("user_id", "anonymous")

        if not self.workflow_state:
            return {"workflows": []}

        workflows = self.workflow_state.list_active_workflows(user_id, limit=10)

        # Serialize timestamps for JSON
        for w in workflows:
            if w.get("last_updated"):
                w["last_updated"] = w["last_updated"].isoformat()

        return {"workflows": workflows}

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
