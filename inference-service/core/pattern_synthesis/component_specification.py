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

    def process_documentation(self, documentation: str) -> Dict[str, Any]:
        """
        Process technical documentation to extract a holistic component specification.
        """
        logger.info("Processing documentation for holistic component extraction")
        
        if not self.model:
            logger.warning("Vertex AI model not initialized. Returning empty specs.")
            return {"components": [], "relationships": [], "execution_order": []}

        prompt = f"""
        Analyze the following technical documentation and extract a comprehensive component specification.
        
        The output must be a valid JSON object with the following structure:
        {{
            "pattern_name": "Name of the pattern",
            "components": [
                {{
                    "id": "unique_component_id",
                    "name": "Component Name",
                    "type": "Resource Type (e.g., AWS::RDS::DBInstance, Apigee::Proxy, GCP::Storage::Bucket)",
                    "attributes": {{
                        "key": "value" // Attributes for IaC/Service Catalog (e.g., instance_type, engine_version)
                    }},
                    "dependencies": [
                        {{
                            "target_component_id": "id_of_upstream_component",
                            "type": "upstream", // or downstream
                            "integration_attributes": [
                                // Attributes needed from the upstream component (e.g., connection_string, arn)
                                {{ "name": "db_endpoint", "source_attribute": "endpoint" }}
                            ]
                        }}
                    ]
                }}
            ]
        }}

        Ensure that:
        1. All components mentioned in the text are included.
        2. Attributes are inferred from the text or set to reasonable defaults if not specified.
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
