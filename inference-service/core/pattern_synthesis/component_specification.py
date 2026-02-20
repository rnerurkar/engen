import json
import logging
import graphlib
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions
from config import Config

logger = logging.getLogger(__name__)

class ComponentSpecification:
    """
    Stage 3: Advanced Component Specification Logic
    
    Extracts a comprehensive component specification from documentation, including:
    - Detailed component attributes for Terraform/Service Catalog.
    - Explicit upstream/downstream relationships with integration requirements.
    - Dependency ordering for provisioning.
    """
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self._init_vertex_ai()
        self._init_search_client()

    def _init_vertex_ai(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction="""You are a Principal Systems Architect. 
                Your task is to extract a comprehensive component specification from technical documentation.
                Focus on:
                1. Identifying all infrastructure components.
                2. Determining specific attributes needed for IaC (Terraform modules or Service Catalog).
                3. Mapping precise upstream/downstream relationships.
                4. Identifying integration attributes (e.g., DNS names, connection strings) needed for relationships.
                """
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self.model = None

    def _init_search_client(self):
        """Initialize Vertex AI Search (Discovery Engine) client."""
        try:
            # Vertex AI Search uses 'global' location for data stores usually
            # But client endpoint needs to match
            client_options = (
                ClientOptions(api_endpoint=f"{self.location}-discoveryengine.googleapis.com")
                if self.location != "global" and self.location != "us-central1" # default endpoint is global
                else None
            )
            self.search_client = discoveryengine.SearchServiceClient(client_options=client_options)
            
            self.data_store_id = getattr(Config, "VERTEX_SEARCH_CATALOG_STORE_ID", "component-catalog-ds")
            # Serving config is typically in 'global' for search
            self.search_serving_config = self.search_client.serving_config_path(
                project=self.project_id,
                location="global", 
                data_store=self.data_store_id,
                serving_config="default_config",
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI Search Client: {e}")
            self.search_client = None

    def _retrieve_component_schemas(self, query: str) -> str:
        """
        Searches the Vertex AI Search Data Store for component schemas (Terraform modules/SC Products)
        relevant to the architectural pattern.
        """
        if not self.search_client:
            logger.warning("Search client not initialized. Skipping schema retrieval.")
            return ""

        try:
            request = discoveryengine.SearchRequest(
                serving_config=self.search_serving_config,
                query=query,
                page_size=5,
                content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True
                    ),
                    summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                        summary_result_count=5,
                        include_citations=True
                    ),
                ),
            )

            response = self.search_client.search(request=request)
            
            schemas = []
            for result in response.results:
                try:
                    # Try to get structured data first
                    data = result.document.struct_data
                    if not data:
                        # Fallback for derived data
                        data = result.document.derived_struct_data
                    
                    # Convert to string representation
                    schemas.append(json.dumps(dict(data), default=str)) 
                except Exception as inner_e:
                    logger.warning(f"Error parsing search result: {inner_e}")
                    continue

            if schemas:
                return "Available Component Interfaces (Retrieved from Catalog):\n" + "\n---\n".join(schemas)
            else:
                return "No specific component schemas found in catalog."

        except Exception as e:
            logger.error(f"Vertex AI Search failed: {e}")
            return ""

    def process_documentation(self, documentation: str) -> Dict[str, Any]:
        """
        Process technical documentation to extract a holistic component specification.
        """
        logger.info("Processing documentation for holistic component extraction")
        
        # 1. Expand keywords for search
        keyword_prompt = f"Analyze the following documentation and list 5-10 keywords representing the infrastructure resources needed (e.g. 'postgres', 'vpc', 'fargate'). Return only the keywords separated by spaces.\n\nDoc: {documentation[:2000]}"
        search_query = "infrastructure components"
        
        if self.model:
            try:
                kw_response = self.model.generate_content(keyword_prompt)
                search_query = kw_response.text.strip()
            except Exception:
                pass

        # 2. Retrieve relevant schemas using Vertex AI Search
        component_catalog = self._retrieve_component_schemas(search_query)
        
        if not self.model:
            logger.warning("Vertex AI model not initialized. Returning empty specs.")
            return {"components": [], "relationships": [], "execution_order": []}

        prompt = f"""
        Analyze the following technical documentation and extract a comprehensive component specification.
        
        **Component Catalog / Interface Definitions**:
        Use these definitions to determine the correct 'type', `product_id`, and valid 'attributes'.
        
        **CRITICAL - SERVICE CATALOG HANDLING**:
        If a component matches a `service_catalog_product` in the catalog below:
        1. Set its `type` to `service_catalog_product`.
        2. COPY the `service_catalog_product_id` and `provisioning_artifact_id` into the `attributes` object.
        3. Use the parameter names defined in the catalog as the keys in `attributes`.
        
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
                generation_config=GenerationConfig(response_mime_type="application/json", temperature=0.1)
            )
            spec = json.loads(response.text)
            
            # Post-process to add execution order
            spec["execution_order"] = self._calculate_execution_order(spec.get("components", []))
            
            return spec
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            return {"components": [], "error": str(e)}

    def _calculate_execution_order(self, components: List[Dict[str, Any]]) -> List[str]:
        """
        Calculates the topological sort order for provisioning.
        """
        sorter = graphlib.TopologicalSorter()
        comp_map = {c["id"]: c for c in components}
        
        for comp in components:
            sorter.add(comp["id"])
            for dep in comp.get("dependencies", []):
                # If it's an upstream dependency, the upstream component must exist before this one.
                # So this component depends on the target.
                if dep["type"] == "upstream": 
                    target_id = dep["target_component_id"]
                    if target_id in comp_map:
                        sorter.add(comp["id"], target_id)
        
        try:
            return list(sorter.static_order())
        except graphlib.CycleError as e:
            logger.error(f"Circular dependency detected in execution order: {e}")
            # Fallback: return arbitrary order or try to break cycle (omitted for brevity)
            return [c["id"] for c in components]
