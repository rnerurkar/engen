"""
Stage 3: Advanced Component Specification Logic — Real-Time Source Edition

Replaces the VertexAI Search–based catalog retrieval with **real-time** lookups
against GitHub (via MCP or PyGithub) and AWS Service Catalog (via Boto3).

The LLM-based component extraction and dependency ordering logic is preserved
from the legacy version; only the *data source* has changed.
"""

import json
import logging
import graphlib
import asyncio
from typing import Dict, Any, List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from config import Config
from lib.github_mcp_client import GitHubMCPTerraformClient, TerraformModuleSpec
from lib.service_catalog_client import ServiceCatalogClient, ServiceCatalogProductSpec

logger = logging.getLogger(__name__)


class ComponentSpecification:
    """
    Extracts a comprehensive component specification from documentation, including:
    - Detailed component attributes for Terraform / Service Catalog.
    - Explicit upstream/downstream relationships with integration requirements.
    - Dependency ordering for provisioning.

    Two-tier real-time data sourcing:
      Tier 1  →  GitHub MCP Server (or PyGithub fallback) for Terraform modules
      Tier 2  →  AWS Service Catalog via Boto3
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        mcp_session: Optional[Any] = None,
        github_org_repos: Optional[List[str]] = None,
        aws_region: str = "us-east-1",
        aws_profile: Optional[str] = None,
    ):
        self.project_id = project_id
        self.location = location

        # ── Vertex AI (LLM) ──────────────────────────────────────────────
        self._init_vertex_ai()

        # ── Real-time component source clients ───────────────────────────
        self.github_client = GitHubMCPTerraformClient(
            mcp_session=mcp_session,
            org_repos=github_org_repos or [],
        )
        self.sc_client = ServiceCatalogClient(
            region_name=aws_region,
            profile_name=aws_profile,
        )

    # ─── Initialisation ──────────────────────────────────────────────────

    def _init_vertex_ai(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction=(
                    "You are a Principal Systems Architect. "
                    "Your task is to extract a comprehensive component specification "
                    "from technical documentation.\n"
                    "Focus on:\n"
                    "1. Identifying all infrastructure components.\n"
                    "2. Determining specific attributes needed for IaC "
                    "(Terraform modules or Service Catalog).\n"
                    "3. Mapping precise upstream/downstream relationships.\n"
                    "4. Identifying integration attributes (e.g., DNS names, "
                    "connection strings) needed for relationships."
                ),
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self.model = None

    # ─── Real-time Catalog Retrieval ─────────────────────────────────────

    def _retrieve_component_schemas(self, keywords: str) -> str:
        """
        Searches for component interface definitions in **real time** by
        querying GitHub for Terraform modules and AWS Service Catalog for
        products.  Returns a combined text block suitable for the LLM prompt.

        This replaces the legacy VertexAI Search retrieval.
        """
        schemas: List[str] = []

        # Extract individual search terms from the LLM-generated keyword string
        search_terms = [kw.strip().lower() for kw in keywords.replace(",", " ").split() if kw.strip()]
        # De-dup while preserving order
        seen: set = set()
        unique_terms: List[str] = []
        for t in search_terms:
            if t not in seen:
                seen.add(t)
                unique_terms.append(t)

        # Normalise terms to canonical component types
        from lib.component_sources import normalize_component_type
        canonical_types: List[str] = []
        for term in unique_terms:
            ct = normalize_component_type(term)
            if ct not in canonical_types:
                canonical_types.append(ct)

        # ── Tier 1: GitHub ────────────────────────────────────────────────
        loop = _get_or_create_event_loop()
        for comp_type in canonical_types:
            try:
                tf_spec = loop.run_until_complete(
                    self.github_client.search_terraform_module(comp_type)
                )
                if tf_spec:
                    schema = tf_spec.to_catalog_schema()
                    schemas.append(json.dumps(schema, indent=2, default=str))
                    logger.info(f"[GitHub] Found TF module for '{comp_type}' in {tf_spec.source_repo}")
                    continue  # skip SC lookup for this type
            except Exception as e:
                logger.debug(f"GitHub search for '{comp_type}': {e}")

            # ── Tier 2: AWS Service Catalog ───────────────────────────────
            try:
                sc_spec = self.sc_client.search_product(comp_type)
                if sc_spec:
                    schema = sc_spec.to_catalog_schema()
                    schemas.append(json.dumps(schema, indent=2, default=str))
                    logger.info(f"[ServiceCatalog] Found product for '{comp_type}': {sc_spec.product_name}")
            except Exception as e:
                logger.debug(f"SC search for '{comp_type}': {e}")

        if schemas:
            return "Available Component Interfaces (Retrieved in Real-Time):\n" + "\n---\n".join(schemas)
        return "No specific component schemas found from GitHub or Service Catalog."

    # ─── Main Processing ─────────────────────────────────────────────────

    def process_documentation(self, documentation: str) -> Dict[str, Any]:
        """
        Process technical documentation to extract a holistic component specification.
        """
        logger.info("Processing documentation for holistic component extraction")

        # 1. Use LLM to generate search keywords
        keyword_prompt = (
            "Analyze the following documentation and list 5-10 keywords representing "
            "the infrastructure resources needed (e.g. 'postgres', 'vpc', 'fargate'). "
            "Return only the keywords separated by spaces.\n\n"
            f"Doc: {documentation[:2000]}"
        )
        search_query = "infrastructure components"

        if self.model:
            try:
                kw_response = self.model.generate_content(keyword_prompt)
                search_query = kw_response.text.strip()
            except Exception:
                pass

        # 2. Retrieve relevant schemas from real-time sources
        component_catalog = self._retrieve_component_schemas(search_query)

        if not self.model:
            logger.warning("Vertex AI model not initialized. Returning empty specs.")
            return {"components": [], "relationships": [], "execution_order": []}

        # 3. Build LLM extraction prompt (identical to legacy)
        prompt = f"""
        Analyze the following technical documentation and extract a comprehensive component specification.
        
        **Component Catalog / Interface Definitions**:
        Use these definitions to determine the correct 'type', `product_id`, and valid 'attributes'.
        
        **CRITICAL - SERVICE CATALOG HANDLING**:
        If a component matches a `service_catalog_product` in the catalog below:
        1. Set its `type` to `service_catalog_product`.
        2. COPY the `service_catalog_product_id` and `provisioning_artifact_id` into the `attributes` object.
        3. Use the parameter names defined in the catalog as the keys in `attributes`.
        
        **CRITICAL - TERRAFORM MODULE HANDLING**:
        If a component matches a `terraform_module` in the catalog below:
        1. Set its `type` to `terraform_module`.
        2. Include the `module_name` and `source` in the `attributes` object.
        3. Use the variable names defined in the catalog as the keys in `attributes`.
        
        {component_catalog}

        **Guidance**:
        - **Network**: Define VPCs, Subnets, Security Groups.
        - **Compute**: Define EC2 Instances, Lambda Functions, ECS Clusters.
        - **Storage**: Define S3 Buckets, EBS Volumes.
        - **Database**: Define RDS Instances, DynamoDB Tables.
        
        The output must be a valid JSON object following this EXACT structure:
        {{
            "pattern_name": "Three-Tier Web Application",
            "components": [
                {{
                    "id": "vpc-01",
                    "name": "Production VPC",
                    "type": "AWS::EC2::VPC",
                    "attributes": {{
                        "cidr_block": "10.0.0.0/16",
                        "enable_dns_hostnames": true
                    }},
                    "dependencies": []
                }},
                {{
                    "id": "app-cluster",
                    "name": "App ECS Cluster",
                    "type": "AWS::ECS::Cluster",
                    "attributes": {{
                        "capacity_providers": ["FARGATE"]
                    }},
                    "dependencies": [
                        {{
                            "target_component_id": "vpc-01",
                            "type": "upstream",
                            "integration_attributes": [
                                {{ "name": "vpc_id", "source_attribute": "vpc_id" }},
                                {{ "name": "subnets", "source_attribute": "private_subnets" }}
                            ]
                        }}
                    ]
                }},
                {{
                    "id": "app-db",
                    "name": "Primary Database",
                    "type": "AWS::RDS::DBInstance",
                    "attributes": {{
                        "engine": "postgres",
                        "instance_class": "db.t3.micro",
                        "allocated_storage": 20
                    }},
                    "dependencies": [
                         {{
                            "target_component_id": "vpc-01",
                            "type": "upstream",
                            "integration_attributes": [
                                {{ "name": "vpc_security_group_ids", "source_attribute": "default_security_group_id" }}
                            ]
                        }}
                    ]
                }},
                {{
                    "id": "assets-bucket",
                    "name": "Static Assets",
                    "type": "AWS::S3::Bucket",
                    "attributes": {{
                        "versioning": true
                    }},
                    "dependencies": []
                }}
            ]
        }}

        Ensure that:
        1. All components mentioned in the text are included.
        2. Attributes are inferred from the text or set to reasonable defaults based on the Catalog.
        3. Relationships are correctly identified with integration needs.
        
        Documentation:
        {documentation}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    response_mime_type="application/json", temperature=0.1
                ),
            )
            spec = json.loads(response.text)

            # Post-process to add execution order
            spec["execution_order"] = self._calculate_execution_order(
                spec.get("components", [])
            )
            return spec
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            return {"components": [], "error": str(e)}

    # ─── Dependency Ordering ─────────────────────────────────────────────

    @staticmethod
    def _calculate_execution_order(components: List[Dict[str, Any]]) -> List[str]:
        """Calculates the topological sort order for provisioning."""
        sorter = graphlib.TopologicalSorter()
        comp_map = {c["id"]: c for c in components}

        for comp in components:
            sorter.add(comp["id"])
            for dep in comp.get("dependencies", []):
                if dep["type"] == "upstream":
                    target_id = dep["target_component_id"]
                    if target_id in comp_map:
                        sorter.add(comp["id"], target_id)

        try:
            return list(sorter.static_order())
        except graphlib.CycleError as e:
            logger.error(f"Circular dependency detected: {e}")
            return [c["id"] for c in components]


# ─── Helper ──────────────────────────────────────────────────────────────

def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Return the running event loop or create a new one if none exists."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop
