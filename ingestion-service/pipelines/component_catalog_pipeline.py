import os
import json
import logging
import base64
import hcl2
import yaml
import boto3
from typing import List, Dict, Any, Optional
from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile
from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.client_options import ClientOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ComponentCatalogPipeline:
    """
    Ingests infrastructure component definitions (Terraform Modules & CloudFormation Templates)
    from GitHub and indexes them into Vertex AI Search to act as a Component Catalog.
    """
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "engen-project")
        self.location = os.getenv("VERTEX_SEARCH_LOCATION", "global")
        self.data_store_id = os.getenv("VERTEX_SEARCH_CATALOG_STORE_ID", "component-catalog-ds")
        
        # GitHub Config
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_name = os.getenv("GITHUB_INFRA_REPO", "rnerurkar/engen-infrastructure")
        
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required.")

        self.gh = Github(self.github_token)
        
        # Vertex AI Search Client
        client_options = (
            ClientOptions(api_endpoint=f"{self.location}-discoveryengine.googleapis.com")
            if self.location != "global"
            else None
        )
        self.client = discoveryengine.DocumentServiceClient(client_options=client_options)
        
        # AWS Service Catalog Client
        try:
            self.sc_client = boto3.client('servicecatalog')
        except Exception as e:
            logger.warning(f"Failed to initialize AWS Service Catalog client: {e}")
            self.sc_client = None


    def run(self):
        """Main execution flow."""
        logger.info(f"Starting Component Catalog Ingestion for repo: {self.repo_name}")
        
        try:
            repo = self.gh.get_repo(self.repo_name)
            documents = []

            # 1. Process Terraform Modules
            tf_docs = self._process_terraform_modules(repo)
            documents.extend(tf_docs)
            logger.info(f"Extracted {len(tf_docs)} Terraform module schemas.")

            # 2. Process Service Catalog/CloudFormation Products (via AWS API)
            sc_docs = self._process_aws_service_catalog()
            documents.extend(sc_docs)
            logger.info(f"Extracted {len(sc_docs)} AWS Service Catalog product schemas.")
            
            # (Note: Original CFN git scanning removed in favor of direct SC query)

            # 3. Index to Vertex AI Search
            if documents:
                self._index_documents(documents)
            else:
                logger.warning("No documents found to index.")

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)

    def _process_terraform_modules(self, repo: Repository) -> List[discoveryengine.Document]:
        """Scans 'modules/' directory for variables.tf and creates schemas."""
        docs = []
        try:
            # Assuming modules are in a root 'modules' folder
            contents = repo.get_contents("modules")
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(repo.get_contents(file_content.path))
                elif file_content.name == "variables.tf":
                    # We found a module definition
                    module_path = os.path.dirname(file_content.path)
                    module_name = os.path.basename(module_path)
                    
                    schema = self._parse_terraform_variables(file_content)
                    if schema:
                        doc = self._create_vertex_document(
                            id=f"tf-{module_name}",
                            title=f"Terraform Module: {module_name}",
                            category="Terraform Module",
                            content=json.dumps(schema, indent=2),
                            uri=file_content.html_url
                        )
                        docs.append(doc)
        except Exception as e:
            logger.warning(f"Error processing Terraform modules: {e}")
        return docs

    def _process_aws_service_catalog(self) -> List[discoveryengine.Document]:
        """Fetch products from AWS Service Catalog API."""
        docs = []
        if not self.sc_client:
            logger.info("Skipping Service Catalog sync (no boto3 client).")
            return docs
            
        try:
            logger.info("Scanning AWS Service Catalog...")
            paginator = self.sc_client.get_paginator('search_products')
            for page in paginator.paginate():
                for product_view in page.get('ProductViewSummaries', []):
                    product_id = product_view['ProductId']
                    product_name = product_view['Name']
                    
                    # Get Versions (Finding the Latest)
                    try:
                        versions = self.sc_client.list_provisioning_artifacts(ProductId=product_id)
                        artifacts = sorted(
                            versions.get('ProvisioningArtifactDetails', []),
                            key=lambda x: x['CreatedTime'],
                            reverse=True
                        )
                        
                        if not artifacts:
                            continue
                            
                        # Latest Artifact
                        latest = artifacts[0]
                        artifact_id = latest['Id']
                        artifact_name = latest['Name']
                        
                        # Get Parameters
                        params_resp = self.sc_client.describe_provisioning_parameters(
                            ProductId=product_id,
                            ProvisioningArtifactId=artifact_id
                        )
                        
                        parameters = {}
                        for p in params_resp.get('ProvisioningArtifactParameters', []):
                            parameters[p['ParameterKey']] = {
                                "type": p.get('ParameterType', 'String'),
                                "description": p.get('Description', ''),
                                "default": p.get('ParameterDefaultValue', "<<REQUIRED>>"),
                                "constraints": p.get('ParameterConstraints', {}),
                                "is_no_echo": p.get('IsNoEcho', False)
                            }
                        
                        # Create Schema Definition
                        schema = {
                            "type": "service_catalog_product",
                            "attributes": {
                                "service_catalog_product_id": product_id,
                                "service_catalog_product_name": product_name,
                                "provisioning_artifact_id": artifact_id,
                                "provisioning_artifact_name": artifact_name,
                                "parameters": parameters
                            }
                        }
                        
                        doc = self._create_vertex_document(
                            id=f"sc-{product_id}",
                            title=f"Service Catalog Product: {product_name} ({artifact_name})",
                            category="Service Catalog Product",
                            content=json.dumps(schema, indent=2),
                            uri=f"arn:aws:servicecatalog:::product/{product_id}"
                        )
                        docs.append(doc)
                        logger.info(f"Indexed SC Product: {product_name}")
                        
                    except Exception as inner_e:
                        logger.warning(f"Failed to process product {product_name}: {inner_e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error querying AWS Service Catalog: {e}")
            
        return docs

    def _parse_terraform_variables(self, content_file: ContentFile) -> Optional[Dict[str, Any]]:
        """Parses variables.tf content using python-hcl2."""
        try:
            content_str = base64.b64decode(content_file.content).decode("utf-8")
            parsed = hcl2.loads(content_str)
            
            variables = {}
            for entry in parsed.get("variable", []):
                for name, config in entry.items():
                    # Extract type, description, default
                    var_type = config.get("type", "any")
                    desc = config.get("description", "No description")
                    default = config.get("default", "<<REQUIRED>>")
                    
                    variables[name] = {
                        "type": str(var_type),
                        "description": desc,
                        "default": default
                    }
                    
            return {
                "type": "terraform_module",
                "source": content_file.path,
                "attributes": variables
            }
        except Exception as e:
            logger.error(f"Failed to parse HCL for {content_file.path}: {e}")
            return None

    def _process_cloudformation_templates(self, repo: Repository) -> List[discoveryengine.Document]:
        """Scans 'service-catalog/' directory for templates and creates schemas."""
        docs = []
        try:
            # Assuming SC products are in 'service-catalog'
            contents = repo.get_contents("service-catalog")
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(repo.get_contents(file_content.path))
                elif file_content.name.endswith((".yaml", ".yml", ".json")):
                    # Found a CFN template
                    product_name = os.path.splitext(file_content.name)[0]
                    
                    schema = self._parse_cfn_parameters(file_content)
                    if schema:
                        doc = self._create_vertex_document(
                            id=f"sc-{product_name}",
                            title=f"Service Catalog Product: {product_name}",
                            category="Service Catalog Product",
                            content=json.dumps(schema, indent=2),
                            uri=file_content.html_url
                        )
                        docs.append(doc)
        except Exception as e:
            logger.warning(f"Error processing Service Catalog templates: {e}")
        return docs

    def _parse_cfn_parameters(self, content_file: ContentFile) -> Optional[Dict[str, Any]]:
        """Parses CloudFormation Parameters section."""
        try:
            content_str = base64.b64decode(content_file.content).decode("utf-8")
            # Parse YAML (JSON is valid YAML)
            template = yaml.safe_load(content_str)
            
            parameters = {}
            for name, config in template.get("Parameters", {}).items():
                parameters[name] = {
                    "type": config.get("Type", "String"),
                    "description": config.get("Description", ""),
                    "default": config.get("Default", "<<REQUIRED>>")
                }
                
            return {
                "type": "service_catalog_product",
                "source": content_file.path,
                "attributes": parameters
            }
        except Exception as e:
            logger.error(f"Failed to parse CFN for {content_file.path}: {e}")
            return None

    def _create_vertex_document(self, id: str, title: str, category: str, content: str, uri: str) -> discoveryengine.Document:
        """Constructs a Vertex AI Search Document object."""
        return discoveryengine.Document(
            id=id,
            schema_id="default_schema", # Or specific schema if configured
            struct_data={
                "title": title,
                "category": category,
                "uri": uri,
                "original_content": content # The full JSON schema for checking
            },
            content=discoveryengine.Document.Content(
                mime_type="application/json",
                raw_bytes=content.encode("utf-8")
            )
        )

    def _index_documents(self, documents: List[discoveryengine.Document]):
        """Uploads documents to Vertex AI Search."""
        parent = self.client.branch_path(
            project=self.project_id,
            location=self.location,
            data_store=self.data_store_id,
            branch="default_branch",
        )

        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            request_metadata=discoveryengine.RequestMetadata(user_id="engen-ingestion-service"),
            inline_source=discoveryengine.ImportDocumentsRequest.InlineSource(
                documents=documents
            ),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
        )

        operation = self.client.import_documents(request=request)
        logger.info(f"Waiting for import operation {operation.operation.name} to complete...")
        response = operation.result()
        logger.info(f"Import completed. Metadata: {response}")

if __name__ == "__main__":
    pipeline = ComponentCatalogPipeline()
    pipeline.run()
