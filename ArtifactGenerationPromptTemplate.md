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
{
    "pattern_name": "Three-Tier Web Application",
    "components": [
        {
            "id": "vpc-01",
            "name": "Production VPC",
            "type": "AWS::EC2::VPC",
            "attributes": {
                "cidr_block": "10.0.0.0/16",
                "enable_dns_hostnames": true
            },
            "dependencies": []
        },
        {
            "id": "app-cluster",
            "name": "App ECS Cluster",
            "type": "AWS::ECS::Cluster",
            "attributes": {
                "capacity_providers": ["FARGATE"]
            },
            "dependencies": [
                {
                    "target_component_id": "vpc-01",
                    "type": "upstream",
                    "integration_attributes": [
                        { "name": "vpc_id", "source_attribute": "vpc_id" },
                        { "name": "subnets", "source_attribute": "private_subnets" }
                    ]
                }
            ]
        },
        {
            "id": "app-db",
            "name": "Primary Database",
            "type": "AWS::RDS::DBInstance",
            "attributes": {
                "engine": "postgres",
                "instance_class": "db.t3.micro",
                "allocated_storage": 20
            },
            "dependencies": [
                    {
                    "target_component_id": "vpc-01",
                    "type": "upstream",
                    "integration_attributes": [
                        { "name": "vpc_security_group_ids", "source_attribute": "default_security_group_id" }
                    ]
                }
            ]
        },
        {
            "id": "assets-bucket",
            "name": "Static Assets",
            "type": "AWS::S3::Bucket",
            "attributes": {
                "versioning": true
            },
            "dependencies": []
        }
    ]
}

Ensure that:
1. All components mentioned in the text are included.
2. Attributes are inferred from the text or set to reasonable defaults if not specified.
3. Relationships are correctly identified with integration needs.

**Component Catalog**:
The following components are available in the Service Catalog. Use these definitions to determine the correct 'type' and valid 'attributes'.
{component_catalog}

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

