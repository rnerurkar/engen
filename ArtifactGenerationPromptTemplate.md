# Artifact Generation Prompt Templates

This document details the exact prompts used by the `ComponentSpecificationAgent` and `ArtifactGenerationAgent` to generate the complete Component Specification and subsequent Infrastructure as Code (IaC) templates and Boilerplate code. These prompts are located in `inference-service/core/pattern_synthesis/component_specification.py` and `inference-service/core/pattern_synthesis/artifact_generator.py`.

## 1. Component Specification Prompt (`ComponentSpecificationAgent`)

This prompt is used to extract a holistic, structured component specification from the generated pattern documentation. It moves beyond simple entity extraction to identify relationships, dependencies, and integration attributes required for IaC.

### Prompt Template

```python
# 1. Keyword Extraction (Pre-step)
keyword_prompt = f"Analyze the following documentation and list 5-10 keywords representing the infrastructure resources needed (e.g. 'postgres', 'vpc', 'fargate'). Return only the keywords separated by spaces.\n\nDoc: {documentation[:2000]}"

# 2. Main Specification Prompt
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

        Documentation:
        {documentation}
        """
```

---

## 2. Full Artifact Generation Prompt (`ArtifactGenerationAgent`)

This prompt takes the structured component specification from the previous step AND the original documentation to generate a comprehensive artifact bundle. This includes the full Infrastructure as Code (IaC) files and application boilerplate.

### Prompt Template

```python
prompt = f"""
        **Context**:
        You have a comprehensive component specification (JSON) and pattern documentation text.
        Your goal is to generate the complete Infrastructure as Code (IaC) and necessary boilerplate code for a reference implementation.

        **Decision Logic: IaC Framework Selection**:
        - **Primary Framework**: The preferred IaC framework is **{iac_preference.upper()}**.
        - **Service Catalog vs Raw**: 
            - **Trigger**: If a component specification contains `attributes.service_catalog_product_name` or `attributes.service_catalog_product_id`.
            - **Action**: Generate a **Service Catalog Provisioning Resource** (`AWS::ServiceCatalog::CloudFormationProvisionedProduct` for CloudFormation).
            - **Constraint 1 (Versioning)**: You MUST include `ProvisioningArtifactName` (default to "v1.0" or "Latest" if using name) or `ProvisioningArtifactId` (if available in spec).
            - **Constraint 2 (Parameters)**: Parameters must be passed via the `ProvisioningParameters` property as a list of Key/Value pairs, NOT as a standard property map.
            
            *Example of required CFN structure*:
            ```yaml
            Type: AWS::ServiceCatalog::CloudFormationProvisionedProduct
            Properties:
              ProductName: "INSERT_PRODUCT_NAME"
              ProvisioningArtifactName: "v1.0"
              ProvisioningParameters:
                - Key: "ParamNameFromInterface"
                  Value: "ParamValue"
            ```
            
            - Otherwise (if no Service Catalog attributes exist), generate standard resources (e.g., `AWS::S3::Bucket`).
        
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
```

