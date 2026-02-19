# Artifact Generation Prompt Templates

This document details the exact prompts used by the `ComponentSpecificationAgent` and `ArtifactGenerationAgent` to generate the complete Component Specification and subsequent Infrastructure as Code (IaC) templates and Boilerplate code. These prompts are located in `inference-service/core/pattern_synthesis/component_specification.py` and `inference-service/core/pattern_synthesis/artifact_generator.py`.

## 1. Component Specification Prompt (`ComponentSpecificationAgent`)

This prompt is used to extract a holistic, structured component specification from the generated pattern documentation. It moves beyond simple entity extraction to identify relationships, dependencies, and integration attributes required for IaC.

### Prompt Template

```markdown
# Role & Objective
You are a Principal Systems Architect.
Task: Analyze the following technical documentation and extract a comprehensive component specification.

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
```

---

## 2. Full Artifact Generation Prompt (`ArtifactGenerationAgent`)

This prompt takes the structured component specification from the previous step AND the original documentation to generate a comprehensive artifact bundle. This includes the full Infrastructure as Code (IaC) files and application boilerplate.

### Prompt Template

```markdown
# Role & Objective
You are a Principal Cloud Architect and DevOps Engineer.
Task: Generate complete, production-ready Infrastructure as Code (IaC) and application boilerplate code for the described architectural pattern.

# Critical Constraints
1. **Holistic Implementation**: Do not generate snippets. Generate the COMPLETE file contents for the reference implementation.
2. **Consistency**: Ensure variable names, resource IDs, and references match between the IaC and the Boilerplate code.
3. **Security**: Implement best practices (IAM roles, Security Groups, Encryption) by default.
4. **Validation Feedback**: If a critique is provided, you MUST address the specific points raised in the previous validation attempt.

# Input 1: Component Specification (JSON)
{component_spec}

# Input 2: Pattern Documentation (Text)
{pattern_documentation}

# (Optional) Input 3: Validation Critique
{critique}

# Logic Protocol
1. **IaC Generation**: Create `main.tf`, `variables.tf`, and `outputs.tf` (for Terraform) that provision all components in the spec.
    - Wire dependencies using the `integration_attributes` defined in the spec.
2. **Boilerplate Generation**: Create Python/Node.js/Shell code for the application logic.
    - **API Components**: Include proxy configuration, auth policies, or handler code.
    - **Database Components**: Include schema initialization or connection logic.
    - **Compute**: Include the application handler code (e.g., Lambda handler, Container Dockerfile).

# Output Format
Return a valid JSON object with the following structure (do not use Markdown code blocks):
{
    "iac_templates": {
        "terraform": {
            "main.tf": "...",
            "variables.tf": "...",
            "outputs.tf": "..."
        },
        "cloudformation": {
            "template.yaml": "..." // Only if applicable/requested
        }
    },
    "boilerplate_code": {
        "component_id_or_name": {
            "files": {
                "filename.ext": "full content of the file..." 
            },
            "instructions": "Brief steps to build/run..."
        }
    }
}
```

