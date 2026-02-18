import json
import logging
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.cloud import storage
from config import Config

logger = logging.getLogger(__name__)

class ArtifactValidator:
    """
    Stage 5: Artifact Validation (Pattern Synthesis)
    
    Validates generated Infrastructure as Code (IaC) and application boilerplate
    matrices against a specific quality rubric.
    """
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self._init_vertex_ai()
        try:
            self.storage_client = storage.Client(project=project_id)
            self.bucket_name = Config.GCS_IAC_TEMPLATES_BUCKET
        except Exception as e:
            logger.warning(f"Failed to initialize Storage Client: {e}")
            self.storage_client = None

    def _init_vertex_ai(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction="You are a Principal Code Reviewer and Security Architect. Your task is to deeply analyze Infrastructure as Code and Application Boilerplate for correctness, security, and completeness."
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            self.model = None

    def _fetch_template(self, folder: str, filename: str) -> str:
        """Fetches a sample template from GCS."""
        if not self.storage_client:
            return ""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"{folder}/{filename}")
            if blob.exists():
                return blob.download_as_text()
            logger.warning(f"Sample template {folder}/{filename} not found in {self.bucket_name}")
            return ""
        except Exception as e:
            logger.error(f"Error fetching sample template: {e}")
            return ""

    def validate_artifacts(self, artifacts: Dict[str, Any], component_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the artifacts against the component specification and strict quality rubric.
        """
        logger.info("Validating artifacts against rubric")

        if not self.model:
            return {"score": 0, "status": "FAILED", "feedback": "Validator model not initialized", "issues": []}

        # Fetch golden samples
        tf_sample = self._fetch_template("terraform", "sample.tf")
        cf_sample = self._fetch_template("cloudformation", "sample.yaml")

        prompt = f"""
        **Task**: Validate the provided Artifacts (IaC + Code) against the Component Specification using the Quality Rubric.

        **Reference Standards (Golden Samples)**:
        Use these samples as the benchmark for code style, structure, and best practices.
        
        --- Terraform Sample ---
        {tf_sample if tf_sample else "N/A"}
        
        --- CloudFormation Sample ---
        {cf_sample if cf_sample else "N/A"}
        
        **Component Specification**:
        {json.dumps(component_spec, indent=2)}

        **Generated Artifacts**:
        {json.dumps(artifacts, indent=2)}

        **Quality Rubric**:
        1. **Syntactic Correctness** (Critical): 
           - Is the Terraform/CloudFormation valid syntax?
           - Is the Python boilerplate valid syntax?
        2. **Completeness** (Critical):
           - Are ALL components from the spec represented in the artifacts?
        3. **Integration Wiring** (Critical):
           - Do upstream components export necessary outputs (e.g., DB Endpoints)?
           - Do downstream components consume these outputs correctly (e.g., variable references)?
        4. **Security** (High):
           - Are specific security attributes (IAM, Security Groups) present?
           - No hardcoded secrets.
        5. **Boilerplate Functional Relevance** (Medium):
           - Does the "Hello World" code actually demonstrate the integration (e.g., connecting to the DB)?
        6. **Adherence to Best Practices** (Medium):
           - Does the generated code follow the patterns and constructs used in the Reference Standards?
        
        **Output Format**:
        Return a valid JSON object:
        {{
            "score": <0-100 integer>,
            "status": "PASS" | "NEEDS_REVISION", // PASS if score >= 85 and no Critical/High issues
            "issues": [
                {{
                    "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
                    "component": "Component Name or 'General'",
                    "description": "Detailed description of the issue",
                    "suggestion": "How to fix it"
                }}
            ],
            "feedback": "General summary for the developer agent."
        }}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(response_mime_type="application/json", temperature=0.1)
            )
            validation_result = json.loads(response.text)
            return validation_result
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "score": 0, 
                "status": "ERROR", 
                "feedback": f"Validation process error: {str(e)}", 
                "issues": []
            }
