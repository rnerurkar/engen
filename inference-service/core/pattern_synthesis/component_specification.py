import json
import logging
import graphlib
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import storage
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
        self._init_gcs()

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

    def _init_gcs(self):
        try:
            self.storage_client = storage.Client(project=self.project_id)
            self.bucket_name = getattr(Config, "GCS_CONFIG_BUCKET", "engen-config")
        except Exception as e:
            logger.error(f"Failed to initialize GCS Client: {e}")
            self.storage_client = None

    def _fetch_component_interfaces(self) -> str:
        """
        Retrieves interface definitions (Terraform variables or Service Catalog parameters) 
        from GCS to guide the LLM on valid attributes.
        """
        if not self.storage_client:
            return ""
            
        interfaces = []
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            # Assumption: Interfaces are stored in a 'interfaces/' prefix or similar
            # For this implementation, we'll look for a 'component_catalog.json' which is a summary
            blob = bucket.blob("component_catalog.json")
            if blob.exists():
                return f"Available Component Interfaces:\n{blob.download_as_text()}"
        except Exception as e:
            logger.warning(f"Failed to fetch component interfaces: {e}")
            
        return ""

    def process_documentation(self, documentation: str) -> Dict[str, Any]:
        """
        Process technical documentation to extract a holistic component specification.
        """
        logger.info("Processing documentation for holistic component extraction")
        
        # 1. Fetch Component Interfaces to ground the attributes
        component_catalog = self._fetch_component_interfaces()

        if not self.model:
            logger.warning("Vertex AI model not initialized. Returning empty specs.")
            return {"components": [], "relationships": [], "execution_order": []}

        prompt = f"""
        Analyze the following technical documentation and extract a comprehensive component specification.
        
        **Component Catalog / Interface Definitions**:
        Use these definitions to determine the correct 'type' and valid 'attributes' for each component.
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
