"""
ADK Workflow Step Agents — Phase 1 & Phase 2
=============================================
Each class is a ``WorkflowAgent`` step that operates on a shared
``WorkflowContext``.  They are composed into ``SequentialAgent``
(top-level) containing ``LoopAgent`` sub-workflows.

Phase 1 — Doc Generation
~~~~~~~~~~~~~~~~~~~~~~~~~
DocGenerationWorkflow (SequentialAgent)
  ├─ VisionAnalysisStep           — Gemini Vision image description
  ├─ DonorRetrievalStep           — Vertex AI Search donor lookup
  ├─ ContentRefinementLoop (LoopAgent, max 3, exit_key="approved")
  │    ├─ PatternGenerateStep     — core doc generation (Gemini Pro)
  │    ├─ HADRSectionsStep        — HA/DR retrieval + generation
  │    │     (parallel retrieval + donor extraction, then 4-strategy gen)
  │    └─ FullDocReviewStep       — reviews ENTIRE doc incl. HA/DR
  └─ HADRDiagramStep              — async diagram gen + GCS upload

Phase 2 — Artifact Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ArtifactWorkflow (SequentialAgent)
  ├─ ComponentSpecStep            — extract component spec from docs
  └─ ArtifactRefinementLoop (LoopAgent, max 3, exit_key="validation_passed")
       ├─ ArtifactGenerateStep    — generate IaC + boilerplate
       └─ ArtifactValidateStep    — validate against quality rubric

Performance Optimisations Applied
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. In-process calls — no HTTP/A2A overhead, no session management,
   no serialisation.  Eliminates the 30 s default timeout problem.
2. Parallel retrieval + donor extraction inside HADRSectionsStep
   via asyncio.gather (saves ~5-10 s).
3. Service names extracted ONCE and cached in context (was called
   twice before).
4. Diagram Semaphore raised to 6 (from 4) → 2 rounds instead of 3.
5. HA/DR now inside the refinement loop so the reviewer critiques
   the full document (core + HA/DR) and the generator can fix any
   HA/DR issues on subsequent iterations.
6. Phase 2 artifact gen/validate loop runs in-process just like
   Phase 1 — no A2A HTTP calls, no serialisation overhead.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional

from lib.adk_core import WorkflowAgent, WorkflowContext

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Vision Analysis
# ──────────────────────────────────────────────────────────────────────────────


class VisionAnalysisStep(WorkflowAgent):
    """
    Analyse the architecture diagram using Gemini Vision
    and store the textual description in the workflow context.

    Reads:  image_bytes
    Writes: description
    """

    def __init__(self):
        super().__init__(name="VisionAnalysisStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        generator = ctx.get("_generator")  # core.generator.PatternGenerator
        image_bytes = ctx.get("image_bytes")

        self.logger.info("Analysing architecture diagram (Gemini Vision)")
        description = await asyncio.to_thread(
            generator.generate_search_description, image_bytes
        )
        ctx.set("description", description)
        self.logger.info(f"Vision analysis complete ({len(description)} chars)")
        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Donor Retrieval
# ──────────────────────────────────────────────────────────────────────────────


class DonorRetrievalStep(WorkflowAgent):
    """
    Retrieve the best-matching donor pattern from Vertex AI Search
    to serve as a structural and stylistic template.

    Reads:  title, description
    Writes: donor_context
    """

    def __init__(self):
        super().__init__(name="DonorRetrievalStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        retriever = ctx.get("_retriever")  # core.retriever.VertexRetriever
        title = ctx.get("title")
        description = ctx.get("description")

        self.logger.info("Retrieving donor pattern")
        donor_context = await asyncio.to_thread(
            retriever.get_best_donor_pattern, title, description
        )
        if not donor_context:
            raise ValueError("Failed to retrieve donor pattern")
        ctx.set("donor_context", donor_context)
        self.logger.info("Donor pattern retrieved successfully")
        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Loop Step A: Pattern Generation
# ──────────────────────────────────────────────────────────────────────────────


class PatternGenerateStep(WorkflowAgent):
    """
    Generate the core pattern documentation sections using the
    diagram, donor context, and optional critique from a previous
    review iteration.

    Reads:  image_bytes, donor_context, title, critique (optional)
    Writes: generated_sections
    """

    def __init__(self):
        super().__init__(name="PatternGenerateStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        generator = ctx.get("_generator")
        image_bytes = ctx.get("image_bytes")
        donor_context = ctx.get("donor_context")
        title = ctx.get("title")
        critique = ctx.get("critique")
        iteration = ctx.get("loop_iteration", 1)

        self.logger.info(
            f"Generating pattern sections (iteration {iteration})"
        )
        sections = await asyncio.to_thread(
            generator.generate_pattern,
            image_bytes=image_bytes,
            donor_context=donor_context,
            user_title=title,
            critique=critique,
        )
        ctx.set("generated_sections", sections)
        self.logger.info(
            f"Generated {len(sections)} sections "
            f"(iteration {iteration})"
        )
        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Loop Step B: HA/DR Section Generation  (with parallel optimisations)
# ──────────────────────────────────────────────────────────────────────────────


class HADRSectionsStep(WorkflowAgent):
    """
    Generate HA/DR documentation sections using direct in-process
    calls to the core retriever and generator modules.

    **Optimisation**: Steps 2 (bulk HA/DR retrieval) and 3 (donor
    extraction) are independent and run in parallel via asyncio.gather.

    On iterations > 1, if the reviewer did not specifically critique
    the HA/DR section, this step is skipped to save tokens.

    Reads:  generated_sections, donor_context, _hadr_retriever,
            _hadr_generator
    Writes: hadr_sections, service_names (cached), generated_sections
            (with HA/DR merged)
    """

    def __init__(self):
        super().__init__(name="HADRSectionsStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        iteration = ctx.get("loop_iteration", 1)
        generated_sections = ctx.get("generated_sections") or {}
        donor_context = ctx.get("donor_context") or {}

        # On iterations > 1, only regenerate HA/DR if the reviewer
        # specifically flagged it.  This saves 4 × Gemini calls per
        # re-iteration when only core sections need fixing.
        if iteration > 1:
            critique_text = ctx.get("critique", "") or ""
            hadr_flagged = any(
                kw in critique_text.lower()
                for kw in ("ha/dr", "hadr", "disaster recovery",
                           "high availability", "failover", "failback")
            )
            if not hadr_flagged and ctx.get("hadr_sections"):
                self.logger.info(
                    f"Skipping HA/DR regeneration (iteration {iteration}): "
                    f"reviewer did not flag HA/DR"
                )
                # Re-merge cached HA/DR into freshly generated sections
                self._merge_hadr(ctx)
                return ctx

        try:
            hadr_sections = await self._generate_hadr(ctx)
            ctx.set("hadr_sections", hadr_sections)
        except Exception as e:
            self.logger.error(
                f"HA/DR text generation failed (non-blocking): {e}",
                exc_info=True,
            )
            ctx.set("hadr_sections", {})

        self._merge_hadr(ctx)
        return ctx

    async def _generate_hadr(
        self, ctx: WorkflowContext
    ) -> Dict[str, str]:
        """Core HA/DR generation: retrieve + donor extract (parallel) → generate."""
        generated_sections = ctx.get("generated_sections") or {}
        donor_context = ctx.get("donor_context") or {}
        hadr_retriever = ctx.get("_hadr_retriever")
        hadr_generator = ctx.get("_hadr_generator")

        if not hadr_retriever or not hadr_generator:
            self.logger.warning(
                "HA/DR core modules not available — skipping"
            )
            return {}

        # 1. Extract service names (CPU-only, cached)
        service_names = ctx.get("service_names")
        if not service_names:
            doc_text = "\n".join(str(v) for v in generated_sections.values())
            service_names = _extract_service_names_from_doc(doc_text)
            ctx.set("service_names", service_names)

        if not service_names:
            self.logger.warning(
                "No service names extracted — skipping HA/DR generation"
            )
            return {}

        self.logger.info(
            f"Extracted service names for HA/DR: {service_names}"
        )

        # 2 & 3.  PARALLEL: Retrieve service HA/DR docs + extract donor
        #          HA/DR sections.  These are independent operations.
        donor_html = donor_context.get("html_content", "")

        retriever_task = hadr_retriever.aretrieve_all_services_hadr(
            service_names=service_names
        )
        donor_extract_task = asyncio.to_thread(
            hadr_generator.extract_donor_hadr_sections, donor_html
        )

        service_hadr_docs, donor_hadr_sections = await asyncio.gather(
            retriever_task, donor_extract_task
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

        # 5. Generate all 4 DR strategy sections (internal asyncio.gather)
        hadr_sections = await hadr_generator.agenerate_hadr_sections(
            pattern_context=pattern_context,
            donor_hadr_sections=donor_hadr_sections,
            service_hadr_docs=service_hadr_docs,
            timeout_per_strategy=120.0,
        )

        return hadr_sections

    @staticmethod
    def _merge_hadr(ctx: WorkflowContext) -> None:
        """Merge HA/DR sections into generated_sections['HA/DR']."""
        from core.pattern_synthesis.hadr_diagram_generator import (
            DR_STRATEGIES,
            LIFECYCLE_PHASES,
        )

        generated_sections = ctx.get("generated_sections")
        hadr_sections = ctx.get("hadr_sections") or {}
        diagram_urls = ctx.get("diagram_urls") or {}

        if generated_sections is None:
            generated_sections = {}
            ctx.set("generated_sections", generated_sections)

        if hadr_sections:
            generated_sections["HA/DR"] = _format_hadr_sections(
                hadr_sections, diagram_urls
            )
        else:
            generated_sections["HA/DR"] = (
                "*HA/DR section generation failed. Please complete manually.*"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Loop Step C: Full Document Review  (reviews core + HA/DR)
# ──────────────────────────────────────────────────────────────────────────────


class FullDocReviewStep(WorkflowAgent):
    """
    Review the ENTIRE pattern document — including the HA/DR section
    — against quality guidelines.

    This is a key change from the old A2A architecture where the
    reviewer only saw core sections and HA/DR was generated after
    the loop.  Now the reviewer can specifically critique HA/DR
    quality, enabling HA/DR refinement in subsequent iterations.

    Reads:  generated_sections, donor_context
    Writes: critique, approved
    """

    def __init__(self):
        super().__init__(name="FullDocReviewStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        reviewer = ctx.get("_reviewer")  # core.reviewer.PatternReviewer
        sections = ctx.get("generated_sections")
        donor_context = ctx.get("donor_context")
        iteration = ctx.get("loop_iteration", 1)

        self.logger.info(
            f"Reviewing full document including HA/DR "
            f"(iteration {iteration})"
        )
        critique_result = await asyncio.to_thread(
            reviewer.review_pattern, sections, donor_context
        )

        approved = critique_result.get("approved", False)
        critique_text = critique_result.get("critique")

        ctx.set("critique", critique_text)
        ctx.set("approved", approved)

        if approved:
            self.logger.info(f"Document APPROVED (iteration {iteration})")
        else:
            self.logger.info(
                f"Document needs revision (iteration {iteration}): "
                f"{(critique_text or '')[:200]}"
            )

        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Post-Loop Step: HA/DR Diagram Generation
# ──────────────────────────────────────────────────────────────────────────────


class HADRDiagramStep(WorkflowAgent):
    """
    Generate SVG + draw.io XML + PNG diagrams for every DR strategy ×
    lifecycle phase combination, upload to GCS, and embed URLs into the
    HA/DR sections.

    Runs AFTER the refinement loop completes (diagrams depend on the
    final HA/DR text).  Non-blocking: failures do not prevent the
    workflow from producing a document.

    **Optimisations Applied**:
    - Semaphore raised to 6 (from 4) → 2 rounds instead of 3
      for 12 diagrams.
    - Service names reused from context (no redundant extraction).

    Reads:  generated_sections, hadr_sections, service_names, title,
            _hadr_diagram_generator, _hadr_diagram_storage
    Writes: diagram_urls, generated_sections (HA/DR re-merged with URLs)
    """

    def __init__(self):
        super().__init__(name="HADRDiagramStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        hadr_sections = ctx.get("hadr_sections") or {}
        if not hadr_sections:
            self.logger.info("No HA/DR sections — skipping diagrams")
            return ctx

        try:
            diagram_urls = await self._generate_and_store(ctx)
            ctx.set("diagram_urls", diagram_urls)
        except Exception as e:
            self.logger.error(
                f"HA/DR diagram generation failed (non-blocking): {e}",
                exc_info=True,
            )
            return ctx

        # Re-merge HA/DR sections with diagram URLs embedded
        HADRSectionsStep._merge_hadr(ctx)
        return ctx

    async def _generate_and_store(
        self, ctx: WorkflowContext
    ) -> Dict:
        """Generate diagrams and upload to GCS."""
        diagram_gen = ctx.get("_hadr_diagram_generator")
        diagram_store = ctx.get("_hadr_diagram_storage")
        hadr_sections = ctx.get("hadr_sections") or {}
        service_names = ctx.get("service_names") or []
        title = ctx.get("title", "untitled")

        if not diagram_gen or not diagram_store:
            self.logger.warning(
                "Diagram core modules not available — skipping"
            )
            return {}

        if not service_names:
            self.logger.warning("No services — skipping diagrams")
            return {}

        pattern_context = {"title": title, "services": service_names}

        # Generate all 12 diagrams — Semaphore(6) for better throughput
        bundle = await diagram_gen.agenerate_all_diagrams(
            pattern_name=title,
            services=service_names,
            hadr_text_sections=hadr_sections,
            pattern_context=pattern_context,
            timeout_per_diagram=180.0,
            max_concurrent=6,  # ← optimisation: was 4
        )

        # Upload all artefacts to GCS in parallel
        async def _upload_one(strategy, phase, artifact):
            try:
                urls = await diagram_store.aupload_diagram_bundle(
                    pattern_name=title,
                    strategy=strategy,
                    phase=phase,
                    svg_content=artifact.svg_content,
                    drawio_xml=artifact.drawio_xml,
                    png_bytes=artifact.png_bytes,
                )
                return (strategy, phase), urls
            except Exception as exc:
                self.logger.error(
                    f"Upload failed {strategy}/{phase}: {exc}"
                )
                return (strategy, phase), {}

        upload_tasks = [
            _upload_one(strategy, phase, artifact)
            for (strategy, phase), artifact in bundle.diagrams.items()
        ]
        results = await asyncio.gather(*upload_tasks)

        url_map = {}
        for (strategy, phase), urls in results:
            url_map[(strategy, phase)] = urls

        self.logger.info(
            f"Generated & stored {len(url_map)} diagram bundles "
            f"for '{title}'"
        )
        return url_map


# ──────────────────────────────────────────────────────────────────────────────
# Shared Utility Functions (moved from OrchestratorAgent)
# ──────────────────────────────────────────────────────────────────────────────


def _extract_service_names_from_doc(doc_text: str) -> list:
    """
    Lightweight extraction of canonical service names from pattern
    documentation using regex matching against known aliases.
    """
    from lib.component_sources import COMPONENT_TYPE_ALIASES

    doc_lower = doc_text.lower()
    found_services: set = set()

    # Canonical type → display name mapping
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
        pattern = r"\b" + re.escape(alias.replace("_", " ")) + r"\b"
        if re.search(pattern, doc_lower):
            display_name = canonical_to_display.get(canonical, canonical)
            found_services.add(display_name)

    # Also check common full service names
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


def _format_hadr_sections(
    hadr_sections: Dict[str, str],
    diagram_urls: Optional[Dict] = None,
) -> str:
    """
    Combine the four individual DR strategy sections into a single
    Markdown block with embedded diagram references.
    """
    from core.pattern_synthesis.hadr_diagram_generator import (
        DR_STRATEGIES,
        LIFECYCLE_PHASES,
    )

    if diagram_urls is None:
        diagram_urls = {}

    parts = ["## High Availability / Disaster Recovery\n"]

    for strategy in DR_STRATEGIES:
        section_text = hadr_sections.get(strategy, "")
        if not section_text:
            parts.append(f"## {strategy}\n\n*Section not generated.*\n")
            continue

        enriched_text = section_text
        for phase in LIFECYCLE_PHASES:
            urls = diagram_urls.get((strategy, phase), {})
            if urls and urls.get("png_url"):
                png_url = urls["png_url"]
                svg_url = urls.get("svg_url", "")
                drawio_url = urls.get("drawio_url", "")

                diagram_block = (
                    f"\n\n**Component Diagram — {phase}**\n\n"
                    f"![{strategy} - {phase}]({png_url})\n\n"
                )
                if svg_url:
                    diagram_block += f"[View SVG]({svg_url})"
                if drawio_url:
                    diagram_block += f" | [Edit in draw.io]({drawio_url})"
                diagram_block += "\n"

                phase_pattern = re.compile(
                    rf"(###\s*{re.escape(phase)}[^\n]*\n)",
                    re.IGNORECASE,
                )
                match = phase_pattern.search(enriched_text)
                if match:
                    insert_pos = match.end()
                    enriched_text = (
                        enriched_text[:insert_pos]
                        + diagram_block
                        + enriched_text[insert_pos:]
                    )
                else:
                    enriched_text += diagram_block

        parts.append(enriched_text)

    return "\n\n---\n\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Artifact Generation Workflow Steps
# ══════════════════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Component Specification Extraction
# ──────────────────────────────────────────────────────────────────────────────


class ComponentSpecStep(WorkflowAgent):
    """
    Extract a holistic component specification from the approved
    pattern documentation.  Uses real-time lookups against GitHub
    (Terraform modules) and AWS Service Catalog to enrich the spec
    with authoritative interface definitions.

    Reads:  full_doc, _component_spec_engine
    Writes: component_spec
    """

    def __init__(self):
        super().__init__(name="ComponentSpecStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        engine = ctx.get("_component_spec_engine")
        full_doc = ctx.get("full_doc")

        if not engine:
            raise RuntimeError(
                "ComponentSpecStep: _component_spec_engine not in context"
            )
        if not full_doc:
            raise ValueError("ComponentSpecStep: full_doc is empty")

        self.logger.info(
            "Extracting component specification from documentation"
        )
        spec = await asyncio.to_thread(
            engine.process_documentation, full_doc
        )
        ctx.set("component_spec", spec)

        num_components = len(spec.get("components", []))
        self.logger.info(
            f"Component spec extracted: {num_components} components, "
            f"execution_order={spec.get('execution_order', [])}"
        )
        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Loop Step A: Artifact Generation
# ──────────────────────────────────────────────────────────────────────────────


class ArtifactGenerateStep(WorkflowAgent):
    """
    Generate IaC templates (Terraform / CloudFormation) and application
    boilerplate code from the component specification and approved
    documentation.

    On iterations > 1, incorporates ``artifact_critique`` from the
    previous validation round so the LLM can specifically address the
    flagged issues.

    Reads:  component_spec, full_doc, artifact_critique (optional),
            _artifact_generator_engine
    Writes: artifacts
    """

    def __init__(self):
        super().__init__(name="ArtifactGenerateStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        engine = ctx.get("_artifact_generator_engine")
        spec = ctx.get("component_spec")
        full_doc = ctx.get("full_doc")
        critique = ctx.get("artifact_critique")
        iteration = ctx.get("loop_iteration", 1)

        if not engine:
            raise RuntimeError(
                "ArtifactGenerateStep: _artifact_generator_engine "
                "not in context"
            )

        self.logger.info(
            f"Generating artifacts (iteration {iteration})"
            + (f" — addressing critique" if critique else "")
        )
        artifacts = await asyncio.to_thread(
            engine.generate_full_pattern_artifacts,
            spec,
            full_doc,
            critique,
        )
        ctx.set("artifacts", artifacts)

        # Log a summary of what was generated
        iac_keys = list(artifacts.get("iac_templates", {}).keys())
        boilerplate_keys = list(
            artifacts.get("boilerplate_code", {}).keys()
        )
        self.logger.info(
            f"Artifacts generated (iteration {iteration}): "
            f"IaC={iac_keys}, boilerplate={boilerplate_keys}"
        )
        return ctx


# ──────────────────────────────────────────────────────────────────────────────
# Loop Step B: Artifact Validation
# ──────────────────────────────────────────────────────────────────────────────


class ArtifactValidateStep(WorkflowAgent):
    """
    Validate generated artifacts against the component specification
    and a strict quality rubric covering syntactic correctness,
    completeness, integration wiring, security, and best practices.

    Sets ``validation_passed`` = True in context when artifacts score
    ≥ 85 with no Critical/High issues.  Otherwise stores the textual
    feedback in ``artifact_critique`` so the next generation iteration
    can address the specific issues.

    Reads:  artifacts, component_spec, _artifact_validator_engine
    Writes: validation_passed, artifact_critique, validation_result
    """

    def __init__(self):
        super().__init__(name="ArtifactValidateStep")

    async def run(self, ctx: WorkflowContext) -> WorkflowContext:
        engine = ctx.get("_artifact_validator_engine")
        artifacts = ctx.get("artifacts")
        spec = ctx.get("component_spec")
        iteration = ctx.get("loop_iteration", 1)

        if not engine:
            raise RuntimeError(
                "ArtifactValidateStep: _artifact_validator_engine "
                "not in context"
            )

        self.logger.info(f"Validating artifacts (iteration {iteration})")
        result = await asyncio.to_thread(
            engine.validate_artifacts, artifacts, spec
        )

        # Store full validation result for downstream consumers
        ctx.set("validation_result", result)

        passed = result.get("status") == "PASS"
        ctx.set("validation_passed", passed)

        if passed:
            score = result.get("score", "N/A")
            self.logger.info(
                f"Artifacts PASSED validation "
                f"(iteration {iteration}, score={score})"
            )
        else:
            feedback = result.get("feedback", "")
            score = result.get("score", "N/A")
            num_issues = len(result.get("issues", []))
            ctx.set("artifact_critique", feedback)
            self.logger.info(
                f"Artifacts need revision "
                f"(iteration {iteration}, score={score}, "
                f"{num_issues} issues): {feedback[:200]}"
            )

        return ctx
