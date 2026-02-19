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
    Stage 4: Advanced Artifact Generation
    
    Generates comprehensive Infrastructure as Code (IaC) templates and application boilerplate code
    based on a holistic Component Specification and Pattern Documentation.
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
                system_instruction="You are a Principal Cloud Architect and DevOps Engineer. Your task is to generate complete, production-ready Infrastructure as Code (IaC) and application boilerplate for complex architectural patterns."
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

    def _fetch_golden_samples(self, component_spec: Dict[str, Any]) -> str:
        """
        Retrieves 'Golden Sample' IaC snippets from GCS for the components identified in the spec.
        This provides the LLM with concrete examples of enterprise-approved modules.
        
        Logic:
        1. Parse unique component types from the spec.
        2. Check for existence of sample files in GCS under `terraform/` or `cloudformation/`.
        3. Returns a concatenated string of samples to inject into the prompt.
        """
        if not self.storage_client:
            return ""

        # Using a config bucket for templates
        bucket_name = getattr(Config, "GCS_IAC_TEMPLATES_BUCKET", "engen-iac-templates")
        samples_context = []
        unique_types = set()

        # Extract types safely
        if "components" in component_spec and isinstance(component_spec["components"], list):
            for c in component_spec["components"]:
                if "type" in c:
                    unique_types.add(c["type"])
        
        if not unique_types:
            return ""

        try:
            bucket = self.storage_client.bucket(bucket_name)
            logger.info(f"Fetching Golden Samples for types: {unique_types}")
            
            for c_type in unique_types:
                # Normalize type from "AWS::RDS::DBInstance" to "aws-rds-dbinstance"
                safe_name = c_type.lower().replace("::", "-").replace("_", "-")
                
                # Check for Terraform Sample (preferred)
                tf_blob_path = f"terraform/{safe_name}.tf"
                tf_blob = bucket.blob(tf_blob_path)
                if tf_blob.exists():
                    content = tf_blob.download_as_text()
                    samples_context.append(f"--- GOLDEN SAMPLE: {c_type} (Terraform) ---\n{content}\n")
                
                # Check for CloudFormation Sample
                cf_blob_path = f"cloudformation/{safe_name}.yaml"
                cf_blob = bucket.blob(cf_blob_path)
                if cf_blob.exists():
                    content = cf_blob.download_as_text()
                    samples_context.append(f"--- GOLDEN SAMPLE: {c_type} (CloudFormation) ---\n{content}\n")

        except Exception as e:
            # Non-blocking error - we can proceed without samples
            logger.warning(f"Failed to fetch golden samples from {bucket_name}: {e}")
        
        return "\n".join(samples_context)

    def generate_full_pattern_artifacts(self, component_spec: Dict[str, Any], pattern_documentation: str, critique: str = None) -> Dict[str, Any]:
        """
        Generates the complete set of artifacts for the given pattern.
        """
        logger.info("Generating full pattern artifacts based on comprehensive spec")

        # 1. Fetch Golden Samples from GCS (Terraform & CloudFormation)
        golden_samples = self._fetch_golden_samples(component_spec)
        
        # 2. Determine Pattern Preference (Default to Terraform, can be inferred or Configured)
        # In a real scenario, this might come from the HTTP Request or Project Config.
        iac_preference = component_spec.get("iac_preference", "terraform")

        prompt = f"""
        **Context**:
        You have a comprehensive component specification (JSON) and pattern documentation text.
        Your goal is to generate the complete Infrastructure as Code (IaC) and necessary boilerplate code for a reference implementation.

        **Decision Logic: IaC Framework Selection**:
        - **Primary Framework**: The preferred IaC framework is **{iac_preference.upper()}**.
        - **Service Catalog vs Raw**: 
            - If a component in the spec has `attributes.service_catalog_product_id`, generate a **Service Catalog Provisioning Resource** (e.g., `AWS::ServiceCatalog::CloudFormationProvisionedProduct` in CFN or `aws_servicecatalog_provisioned_product` in Terraform).
            - Otherwise, generate standard resources (e.g., `aws_s3_bucket`) or module usage.
        
        **Enterprise Golden Samples**:
        Use the following approved templates as the strict basis for your generation. 
        Adopt the variable naming conventions, tagging standards, and resource configurations shown here.
        {golden_samples}
        """

        if critique:
             prompt += f"""
        **CRITICAL FEEDBACK FROM PREVIOUS ATTEMPT**:
        The previous attempt to generate artifacts failed validation with the following issues. 
        YOU MUST ADDRESS THESE SPECIFIC POINTS IN THIS ITERATION:
        "{critique}"
        """

        prompt += f"""
        **Input Specification**:
        {json.dumps(component_spec, indent=2)}

        **Input Documentation**:
        {pattern_documentation}

        **Instructions**:
        Generate a JSON object containing the following structure:
        {{
            "iac_templates": {{
                "terraform": {{
                    "main.tf": "...",
                    "variables.tf": "...",
                    "outputs.tf": "..."
                }},
                "cloudformation": {{ // If requested or applicable
                    "template.yaml": "..."
                }}
            }},
            "boilerplate_code": {{
                // Provide code snippets for each component as needed.
                "component_id_or_name": {{
                    "files": {{
                        "filename.py": "content..." 
                    }},
                    "instructions": "steps to run..."
                }}
            }}
        }}

        **Specific Component Handling**:
        1. **API Components**:
           - If a component is an API (e.g., Apigee Proxy), include the configuration for the proxy deploy.
           - Include authentication policies (e.g., OAuth2, API Key) in the boilerplate.
        
        2. **Database Components**:
           - Generate IaC resource definitions (e.g., `aws_db_instance`).
           - Provide output variables for connection strings/endpoints.
           - In the boilerplate for UPSTREAM components (e.g., Compute), show how to retrieve these outputs and connect (e.g., using environment variables).
           - Provide a simple "Hello World" query snippet in the boilerplate.

        3. **Storage Components**:
           - Generate IaC for bucket/volume creation.
           - Ensure IAM policies allow UPSTREAM compute components to access it.
           - Boilerplate in the compute component should demonstrate a simple upload/download operation.

        4. **File Transfer Components**:
           - Generate IaC for the transfer mechanism (e.g., AWS Transfer Family, generic SFTP server).
           - Configure source and destination infrastructure access.
           - Boilerplate should show a sample transfer script.

        **General Guidelines**:
        - Use Terraform modules where appropriate.
        - Ensure all resources are tagged.
        - Output valid JSON only.
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(response_mime_type="application/json", temperature=0.2)
            )
            artifacts = json.loads(response.text)
            return artifacts
        except Exception as e:
            logger.error(f"Full Pattern Generation failed: {e}")
            return {"error": str(e)}

