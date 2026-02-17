# Artifact Generation Prompt Templates

This document details the exact prompts used by the `ArtifactGenerationAgent` to generate Infrastructure as Code (IaC) templates. These prompts are located in `inference-service/core/artifact_generator.py`.

## 1. CloudFormation Prompt (Service Catalog)

This prompt is used when the target artifact type is `cloudformation`. It is specifically designed to handle AWS Service Catalog provisioning when such metadata is present in the component context.

### Prompt Template

```markdown
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
{
  "template.yaml": "..."
}
```

### Context Structure (`{context_str}`)
The `{context_str}` placeholder above is replaced by a JSON object with the following schema:

```json
{
  "metadata": {
    "name": "ComponentName",
    "type": "ComponentType",
    "provider": "aws"
  },
  "module_config": {
    "source": "portfolio-id-if-applicable",
    "sample_code": "provisioning-artifact-id-if-applicable"
  },
  "spec": {
    // Component specific configuration (e.g., InstanceType: "t3.micro")
  },
  "dependencies": {
    "upstream": ["VPC", "Subnet"],
    "upstream_context": {
      "VPC": "vpc-0123456789abcdef0"
    }
  }
}
```

---

## 2. Terraform Prompt (Module Based)

This prompt is used when the target artifact type is `terraform`. It emphasizes the use of Terraform Modules and strict interface compliance.

### Prompt Template

```markdown
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
{
  "variables.tf": "...",
  "main.tf": "...",
  "outputs.tf": "..."
}
```

### Context Structure (`{context_str}`)
The `{context_str}` placeholder covers the component configuration derived from the design pattern:

```json
{
  "metadata": {
    "name": "AppCluster",
    "type": "ECS",
    "provider": "aws"
  },
  "module_config": {
    "source": "git::https://github.com/terraform-aws-modules/terraform-aws-ecs.git",
    "sample_code": "module \"ecs\" { ... }" 
  },
  "spec": {
    "cluster_name": "production-cluster",
    "security": {
      "allow_ingress": ["10.0.0.0/8"]
    }
  },
  "dependencies": {
    "upstream": ["VPC"],
    "upstream_context": {
      "VPC": "vpc-0abc123" 
    }
  }
}
```
