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
    Stage 3: Component Specification Logic
    Core logic for extracting structured component specifications using Gemini 1.5 Pro.
    
    Production Features:
    - **Interface-Driven specification**: Validates extracted specs against authoritative definitions (Terraform variables/Service Catalog).
    - **GCS Integration**: Downloads module schemas from GCS to serve as the "Source of Truth".
    - **Boilerplate Injection**: Automatically adds integration points (outputs/inputs) between components.
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
                system_instruction="You are a Principal Systems Analyst. Your task is to extract structured component specifications and their relationships from technical documentation."
            )
            # Second model instance for Enrichment (specialized instruction)
            self.enrichment_model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction="You are a Technical Interface Specialist. Your task is to map abstract requirements into concrete configuration based on strict Interface Definitions (Terraform variables or CloudFormation Parameters)."
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

    def _get_component_interface(self, component_name: str, component_type: str) -> Optional[str]:
        """
        Retrieves the interface definition (variables.tf or SC product params) from GCS.
        """
        if not self.storage_client:
            return None
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            # Heuristic: path construction based on convention
            # Terraform: terraform-modules/{component_type}/variables.tf
            # Service Catalog: service-catalog-definitions/{product_name}.json
            
            # We assume component_type in the extract is mapped to a module name roughly
            # e.g., "AWS::RDS::DBInstance" -> "rds_instance" or "terraform-aws-rds"
            
            # Simple normalization for demo purposes
            module_name = component_type.lower().replace("::", "-").replace("aws-", "")
            
            # Attempt 1: Terraform Variables
            tf_path = f"terraform-modules/{module_name}/variables.tf"
            blob = bucket.blob(tf_path)
            if blob.exists():
                return f"Terraform Interface (variables.tf):\n{blob.download_as_text()}"
                
            # Attempt 2: Service Catalog Definition
            sc_path = f"service-catalog-definitions/{module_name}.json"
            blob = bucket.blob(sc_path)
            if blob.exists():
                 return f"Service Catalog Interface (JSON):\n{blob.download_as_text()}"

            # Fallback: Check for generic mapping if component_name matches a config
            # (In a real system, we'd look up a catalog registry first)
            
            return None
        except Exception as e:
            logger.warning(f"Error fetching interface for {component_name}: {e}")
            return None

    def _enrich_component_spec(self, component: Dict[str, Any], relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enriches a raw component spec with default values and integration boilerplate 
        based on its authoritative interface.
        """
        interface_def = self._get_component_interface(component["name"], component["type"])
        
        if not interface_def:
            logger.info(f"No authoritative interface found for {component['name']}. Using raw spec.")
            return component

        # Determine upstream/downstream for context
        upstreams = [r["source"] for r in relationships if r["target"] == component["name"]]
        downstreams = [r["target"] for r in relationships if r["source"] == component["name"]]
        
        prompt = f"""
        **Task**: Conform the Raw Component Specification to the Authoritative Interface.
        
        **Context**:
        - Component: {component['name']} ({component['type']})
        - Upstream Dependencies (Inputs): {upstreams}
        - Downstream Dependents (Outputs): {downstreams}
        
        **Raw Specification** (from docs):
        {json.dumps(component.get('spec', {}), indent=2)}
        
        **Authoritative Interface**:
        {interface_def}
        
        **Requirements**:
        1. **Fill Defaults**: If the Interface has a variable with a default, and it's missing in Raw Spec, ADD IT explicitly if it's critical (like instance size), or omit to let IaC handle it. prefer explicit defaults for clarity.
        2. **Boilerplate Integration**: 
           - Identify inputs needed from Upstream (e.g., `vpc_id`, `security_group_ids`). Add them as placeholders like `{{{{upstream.{upstreams[0] if upstreams else 'unknown'}.output_id}}}}`.
           - Ensure mandatory parameters from the Interface are present.
        
        **Output**:
        Return ONLY the JSON object for the new `spec` field.
        """
        
        if self.enrichment_model:
            try:
                response = self.enrichment_model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(response_mime_type="application/json", temperature=0.1)
                )
                enriched_spec = json.loads(response.text)
                # Merge back
                component["spec"] = enriched_spec
                component["enriched"] = True
                return component
            except Exception as e:
                logger.error(f"Enrichment failed for {component['name']}: {e}")
                
        return component

    def process_documentation(self, documentation: str) -> Dict[str, Any]:
        """
        Process technical documentation to extract component specifications using LLM.
        Then enriches them against authoritative sources.
        """
        logger.info("Processing documentation for component extraction")
        
        if not self.model:
            logger.warning("Vertex AI model not initialized. Returning empty specs.")
            return {"components": [], "relationships": []}

        # 1. Raw Extraction
        prompt = f"""
        Analyze the following technical documentation and extract a structured specification of the system components and their relationships.
        
        Output must be valid JSON with two top-level keys:
        1. "components": A list of objects, each having:
           - "name": Unique identifier.
           - "type": Resource type (e.g., "AWS::RDS::DBInstance", "GCP::CloudRun::Service").
           - "spec": Key-value pairs of technical specifications found in the text (engine, instances, etc.).
        2. "relationships": A list of objects, each having:
           - "source": Name of the source component.
           - "target": Name of the target component.
           - "type": Relationship type.

        Documentation:
        {documentation}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(response_mime_type="application/json", temperature=0.1)
            )
            raw_data = json.loads(response.text)
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            return {"components": [], "relationships": []}

        # 2. Enrichment Loop
        components = raw_data.get("components", [])
        relationships = raw_data.get("relationships", [])
        
        enriched_components = []
        for comp in components:
            enriched_comp = self._enrich_component_spec(comp, relationships)
            enriched_components.append(enriched_comp)
            
        return {
            "components": enriched_components,
            "relationships": relationships
        }

    def validate_specs(self, specs: Dict[str, Any]) -> bool:
        """
        Validate the extracted specifications against a JSON schema.
        """
        # Hardcoded schema for self-contained operation
        schema = {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "spec": {"type": "object"}
                        },
                        "required": ["name", "type"]
                    }
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "type": {"type": "string"}
                        },
                        "required": ["source", "target", "type"]
                    }
                }
            },
            "required": ["components", "relationships"]
        }

        try:
            import jsonschema
            jsonschema.validate(instance=specs, schema=schema)
            logger.info("✅ Schema validation passed")
            return True
        except ImportError:
            logger.warning("⚠️ jsonschema library not installed. Skipping strict validation.")
            return "components" in specs and isinstance(specs["components"], list)
        except Exception as e:
            logger.error(f"❌ Schema validation failed: {e}")
            return False

    def get_sorted_execution_plan(self, specs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Returns the components sorted by dependency order (Topological Sort).
        This ensures 'Database' is generated before 'Service' that depends on it.
        """
        components = specs.get("components", [])
        relationships = specs.get("relationships", [])
        
        # Build a lookup map for components
        comp_map = {c["name"]: c for c in components}
        
        # Build the graph
        sorter = graphlib.TopologicalSorter()
        
        # Add all nodes first
        for comp in components:
            sorter.add(comp["name"])
            
        # Add dependencies
        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")
            if source in comp_map and target in comp_map:
                sorter.add(source, target)
        
        try:
            # execution_order is a list of names ["Database", "OrderService"]
            execution_order = list(sorter.static_order())
            return [comp_map[name] for name in execution_order]
        except graphlib.CycleError as e:
            logger.error(f"Circular dependency detected: {e}")
            return components
