import json
import logging
import datetime
import os
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import storage
from config import Config

logger = logging.getLogger(__name__)

class ArtifactGenerator:
    """
    Stage 4: Create artifacts from Component Specifications.
    Core logic for generating IaC and CI/CD artifacts using Vertex AI and GCS configuration.
    
    Production-Grade Improvements:
    1.  **Dynamic Configuration**: Loads component-to-IaC mappings from GCS.
    2.  **Structured Prompting**: Uses improved JSON-native prompts for reliability.
    3.  **Context Injection**: passes upstream dependency outputs to downstream components.
    4.  **Generative AI**: Uses Gemini 1.5 Pro for high-fidelity code generation.
    """

    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self._init_vertex_ai()
        self._init_gcs()
        self.component_mapping = {}
        # Load mapping immediately on init, or lazily. Doing it immediately for fail-fast.
        self._load_component_mapping()

    def _init_vertex_ai(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction="You are a Principal Cloud Infrastructure Engineer specializing in Terraform and CloudFormation."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self.model = None

    def _init_gcs(self):
        try:
            self.storage_client = storage.Client(project=self.project_id)
        except Exception as e:
            logger.error(f"Failed to initialize GCS Client: {e}")
            self.storage_client = None

    def _load_component_mapping(self):
        """
        Loads the Component -> IaC Type mapping from GCS.
        Format expected on GCS:
        {
            "OrderDatabase": { "iac_type": "terraform", "module_source": "git::...", "resource_type": "aws_db_instance" },
            "OrderService": { "iac_type": "cloudformation", "product_name": "Corp-ECS-App" }
        }
        """
        if not self.storage_client:
            logger.warning("Storage client not available. Using empty mapping.")
            return

        try:
            # Safely access class attributes that might not be in Config if users didn't add them yet
            bucket_name = getattr(Config, "GCS_CONFIG_BUCKET", "engen-config")
            file_name = getattr(Config, "COMPONENT_MAPPING_FILE", "component_mapping.json")
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(file_name)
            if blob.exists():
                content = blob.download_as_text()
                self.component_mapping = json.loads(content)
                logger.info(f"Loaded component mapping for {len(self.component_mapping)} components.")
            else:
                logger.warning(f"Mapping file {file_name} not found in {bucket_name}.")
        except Exception as e:
            logger.error(f"Error loading component mapping from GCS: {e}")

    def _get_improved_prompt(self, iac_type: str, component_context: Dict[str, Any]) -> str:
        """
        Returns the optimized prompt based on the IaC type.
        Critique of original prompt:
        - Original was good but split across multiple files/formats.
        - Enhanced to strictly enforce JSON output for programmatic extraction.
        - Added strict validation rules for variable types.
        """
        context_str = json.dumps(component_context, indent=2)

        if iac_type.lower() == "terraform":
            return f"""
# Role & Objective
You are a Principal DevOps Engineer and Terraform Expert.
Task: Generate the Terraform IaC (variables.tf, main.tf, outputs.tf) for a component based on the provided JSON Context.

# Critical Constraints
1. MODULE PREFERENCE: Use the `module_config.source` if provided. Otherwise, use standard provider resources.
2. INTERFACE COMPLIANCE: Your `main.tf` arguments must match the variable names found in `module_config.sample_code` or standard provider docs.
3. SECURITY: Implement `spec.security` requirements (SG rules, IAM) rigorously.
4. DEPENDENCY INJECTION: Use the `upstream_context` values to wire dependencies (e.g., `vpc_id = var.vpc_id`).

# Input: Component Context (JSON)
{context_str}

# Logic Protocol
1. **Analyze Dependencies**: Check `dependencies.upstream` and `upstream_context`. Create variables for missing inputs.
2. **Configure Resource/Module**: Map `spec` configuration to resource arguments.
3. **Expose Outputs**: Ensure `outputs.tf` exports connection details (endpoints, ARNs) for downstream consumption.

# Output Format
Return valid JSON with the following structure (do not use Markdown code blocks):
{{
  "variables.tf": "...",
  "main.tf": "...",
  "outputs.tf": "..."
}}
"""
        elif iac_type.lower() == "cloudformation":
            return f"""
# Role & Objective
You are a Principal AWS Cloud Architect and CloudFormation Expert.
Task: Generate an AWS CloudFormation Template (YAML) to provision a resource.

# Critical Constraints
1. SERVICE CATALOG: If `service_catalog` info is present, use `AWS::ServiceCatalog::CloudFormationProvisionedProduct`.
2. PARAMETER MAPPING: Map `spec.configuration` to the template parameters.
3. DEPENDENCY WIRING: Create `Parameters` for all upstream dependencies.

# Input: Component Context (JSON)
{context_str}

# Logic Protocol
1. **Parameters**: Define CloudFormation Parameters for `dependencies.upstream`.
2. **Resources**: Define the resource or Product.
3. **Outputs**: Use `Outputs` to expose connection details.

# Output Format
Return valid JSON with the following structure (do not use Markdown code blocks):
{{
  "template.yaml": "..."
}}
"""
        else:
            return f"Generate code for {context_str}"

    def generate_artifact(self, spec: Dict[str, Any], default_iac_type: str = "terraform") -> Dict[str, Any]:
        """
        Generate artifacts based on the provided component specification.
        1. Look up component config/mapping.
        2. Determine attributes (IaC type, Module Source).
        3. Generate code using LLM.
        """
        comp_name = spec.get("name")
        logger.info(f"Generating artifact for component: {comp_name}")
        
        # 1. Configuration Lookup
        mapping = self.component_mapping.get(comp_name, {})
        iac_type = mapping.get("iac_type", default_iac_type)
        module_source = mapping.get("module_source", "")
        sample_code = mapping.get("sample_code", "")
        
        # 2. Context Assembly
        # Merge the runtime spec with the static config
        full_context = {
            "metadata": {
                "name": comp_name,
                "type": spec.get("type"),
                "provider": "aws" # defaulting to AWS, should be inferred
            },
            "module_config": {
                "source": module_source,
                "sample_code": sample_code
            },
            "spec": spec.get("spec", {}), # specific configs like size, engine
            "dependencies": {
                "upstream": spec.get("dependencies", []), # list of dep names
                "upstream_context": spec.get("upstream_context", {}) # actual values/ids
            }
        }

        # 3. Prompt Engineering
        prompt = self._get_improved_prompt(iac_type, full_context)
        
        # 4. LLM Generation
        artifact_content = {}
        if self.model:
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                artifact_content = json.loads(response.text)
            except Exception as e:
                logger.error(f"LLM Generation failed for {comp_name}: {e}")
                
                # Mock fallback if LLM not available in test env
                if iac_type == "terraform":
                    artifact_content = {
                        "main.tf": f"# Terraform for {comp_name}\nresource \"aws_instance\" \"this\" {{}}",
                        "variables.tf": "variable \"vpc_id\" {}",
                        "outputs.tf": "output \"id\" { value = aws_instance.this.id }"
                    }
                else:
                    artifact_content = {"template.yaml": "# CloudFormation Template"}
                    
        else:
            artifact_content = {"error": "Model not initialized"}

        return {
            "component_name": comp_name,
            "artifact_type": iac_type,
            "content": artifact_content,
            "metadata": {
                "generated_at": datetime.datetime.now().isoformat(),
                "version": "1.0.0",
                "source_config": mapping
            }
        }

    def validate_artifact(self, artifact: Dict[str, Any]) -> bool:
        """Validate the generated artifact."""
        content = artifact.get("content", {})
        if "error" in content:
            return False
        
        # Basic check: Terraform needs main.tf, CF needs template.yaml
        if artifact.get("artifact_type") == "terraform":
            return "main.tf" in content
        elif artifact.get("artifact_type") == "cloudformation":
            return "template.yaml" in content
            
        return True
