"""
AWS Service Catalog Client for retrieving provisioning parameters.

Used as a fallback when no Terraform module is found via GitHub MCP.
Retrieves product launch parameters and provisioning artifacts directly
from AWS Service Catalog using Boto3.

This replaces the offline ingestion of Service Catalog products
into VertexAI Search that was done by component_catalog_pipeline.py.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ServiceCatalogParameter:
    """Represents a Service Catalog provisioning parameter."""
    key: str
    description: str = ""
    default_value: str = ""
    parameter_type: str = "String"
    is_required: bool = True
    is_no_echo: bool = False
    allowed_values: List[str] = field(default_factory=list)
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class ServiceCatalogProductSpec:
    """Extracted specification from a Service Catalog product."""
    product_id: str
    product_name: str
    provisioning_artifact_id: str
    provisioning_artifact_name: str
    description: str = ""
    parameters: List[ServiceCatalogParameter] = field(default_factory=list)
    product_type: str = ""
    owner: str = ""
    found_via: str = "service_catalog_boto3"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_catalog_schema(self) -> Dict[str, Any]:
        """Convert to the schema format expected by the ComponentSpecification engine.

        Mirrors the format previously indexed by component_catalog_pipeline.py.
        """
        parameters: Dict[str, Any] = {}
        for p in self.parameters:
            parameters[p.key] = {
                "type": p.parameter_type,
                "description": p.description,
                "default": p.default_value if p.default_value else "<<REQUIRED>>",
                "constraints": p.constraints or {},
                "is_no_echo": p.is_no_echo,
            }

        return {
            "type": "service_catalog_product",
            "attributes": {
                "service_catalog_product_id": self.product_id,
                "service_catalog_product_name": self.product_name,
                "provisioning_artifact_id": self.provisioning_artifact_id,
                "provisioning_artifact_name": self.provisioning_artifact_name,
                "parameters": parameters,
            },
        }


class ServiceCatalogClient:
    """
    Client that uses Boto3 to interact with AWS Service Catalog
    to discover products and extract their provisioning parameters.

    This provides *real-time* parameter extraction without pre-indexing.

    Usage:
        client = ServiceCatalogClient(region_name="us-east-1")
        spec = client.search_product("s3_bucket")
    """

    # Mapping component types to Service Catalog product name search terms
    COMPONENT_TO_PRODUCT_PATTERNS: Dict[str, List[str]] = {
        "s3_bucket": ["S3", "Bucket", "Storage"],
        "lambda_function": ["Lambda", "Function", "Serverless"],
        "api_gateway": ["API Gateway", "APIGateway"],
        "dynamodb_table": ["DynamoDB", "NoSQL"],
        "ecs_service": ["ECS", "Container", "Fargate"],
        "eks_cluster": ["EKS", "Kubernetes"],
        "rds_instance": ["RDS", "Database", "Aurora", "PostgreSQL", "MySQL"],
        "sqs_queue": ["SQS", "Queue"],
        "sns_topic": ["SNS", "Topic", "Notification"],
        "vpc": ["VPC", "Network"],
        "cloudfront": ["CloudFront", "CDN"],
        "elasticache": ["ElastiCache", "Redis", "Memcached"],
        "load_balancer": ["ALB", "ELB", "LoadBalancer", "NLB"],
        "iam_role": ["IAM", "Role"],
        "waf": ["WAF", "Firewall"],
        "kms_key": ["KMS", "Key", "Encryption"],
        "secrets_manager": ["SecretsManager", "Secret"],
        "step_function": ["StepFunction", "StateMachine"],
        "codepipeline": ["CodePipeline", "Pipeline", "CICD"],
        "ecr_repository": ["ECR", "ContainerRegistry"],
    }

    def __init__(
        self,
        region_name: str = "us-east-1",
        profile_name: Optional[str] = None,
    ):
        """
        Args:
            region_name: AWS region for Service Catalog.
            profile_name: Optional AWS profile name.
        """
        self.region_name = region_name
        self.profile_name = profile_name
        self._client = None  # lazy-initialized
        self._product_cache: Dict[str, ServiceCatalogProductSpec] = {}

    @property
    def client(self):
        """Lazy-initialize the boto3 Service Catalog client."""
        if self._client is None:
            try:
                import boto3

                session_kwargs: Dict[str, Any] = {"region_name": self.region_name}
                if self.profile_name:
                    session_kwargs["profile_name"] = self.profile_name
                session = boto3.Session(**session_kwargs)
                self._client = session.client("servicecatalog")
            except ImportError:
                logger.warning("boto3 not installed. Install with: pip install boto3")
                self._client = None
            except Exception as e:
                logger.warning(f"Failed to create Service Catalog client: {e}")
                self._client = None
        return self._client

    def search_product(
        self, component_type: str, component_name: str = ""
    ) -> Optional[ServiceCatalogProductSpec]:
        """
        Search for a Service Catalog product matching the component type.

        Args:
            component_type: Infrastructure component type (e.g., "s3_bucket")
            component_name: Optional specific name for targeted search

        Returns:
            ServiceCatalogProductSpec if found, None otherwise
        """
        if not self.client:
            logger.warning("Service Catalog client not available – skipping SC lookup.")
            return None

        cache_key = f"{component_type}:{component_name}"
        if cache_key in self._product_cache:
            return self._product_cache[cache_key]

        patterns = self.COMPONENT_TO_PRODUCT_PATTERNS.get(
            component_type.lower(), [component_type]
        )

        for pattern in patterns:
            try:
                response = self.client.search_products(
                    Filters={"FullTextSearch": [pattern]},
                    PageSize=10,
                )
                for summary in response.get("ProductViewSummaries", []):
                    product_spec = self._extract_product_spec(summary)
                    if product_spec:
                        self._product_cache[cache_key] = product_spec
                        return product_spec
            except Exception as e:
                logger.debug(f"SC search for '{pattern}': {e}")
                continue

        return None

    def _extract_product_spec(
        self, product_summary: Dict[str, Any]
    ) -> Optional[ServiceCatalogProductSpec]:
        """Extract full product spec including provisioning parameters."""
        product_id = product_summary.get("ProductId", "")
        product_name = product_summary.get("Name", "")
        if not product_id:
            return None

        try:
            artifact = self._get_latest_artifact(product_id)
            if not artifact:
                return None

            artifact_id = artifact["Id"]
            artifact_name = artifact.get("Name", "")

            params_response = self.client.describe_provisioning_parameters(
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id,
            )

            parameters: List[ServiceCatalogParameter] = []
            for param in params_response.get("ProvisioningArtifactParameters", []):
                parameter_key = param.get("ParameterKey", "")
                allowed_values: List[str] = []
                constraints = param.get("ParameterConstraints", {})
                if constraints.get("AllowedValues"):
                    allowed_values = constraints["AllowedValues"]

                parameters.append(
                    ServiceCatalogParameter(
                        key=parameter_key,
                        description=param.get("Description", ""),
                        default_value=param.get("DefaultValue", ""),
                        parameter_type=param.get("ParameterType", "String"),
                        is_required=not bool(param.get("DefaultValue")),
                        is_no_echo=param.get("IsNoEcho", False),
                        allowed_values=allowed_values,
                        constraints=constraints if constraints else None,
                    )
                )

            return ServiceCatalogProductSpec(
                product_id=product_id,
                product_name=product_name,
                provisioning_artifact_id=artifact_id,
                provisioning_artifact_name=artifact_name,
                description=product_summary.get("ShortDescription", ""),
                parameters=parameters,
                product_type=product_summary.get("Type", ""),
                owner=product_summary.get("Owner", ""),
                found_via="service_catalog_boto3",
            )
        except Exception as e:
            logger.warning(f"Error extracting spec for SC product {product_name} ({product_id}): {e}")
            return None

    def _get_latest_artifact(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest active provisioning artifact for a product."""
        try:
            response = self.client.list_provisioning_artifacts(ProductId=product_id)
            artifacts = response.get("ProvisioningArtifactDetails", [])

            active_artifacts = [
                a for a in artifacts
                if a.get("Active", False) or a.get("Guidance") != "DEPRECATED"
            ]
            if not active_artifacts:
                return None

            active_artifacts.sort(
                key=lambda a: a.get("CreatedTime", ""), reverse=True
            )
            return active_artifacts[0]
        except Exception as e:
            logger.debug(f"Error getting artifacts for product {product_id}: {e}")
            return None

    def list_all_products(self) -> List[Dict[str, str]]:
        """List all available Service Catalog products. Useful for debugging."""
        if not self.client:
            return []

        products: List[Dict[str, str]] = []
        page_token = None

        while True:
            kwargs: Dict[str, Any] = {"PageSize": 20}
            if page_token:
                kwargs["PageToken"] = page_token

            try:
                response = self.client.search_products(**kwargs)
                for summary in response.get("ProductViewSummaries", []):
                    products.append(
                        {
                            "id": summary.get("ProductId", ""),
                            "name": summary.get("Name", ""),
                            "type": summary.get("Type", ""),
                            "owner": summary.get("Owner", ""),
                            "description": summary.get("ShortDescription", ""),
                        }
                    )
                page_token = response.get("NextPageToken")
                if not page_token:
                    break
            except Exception as e:
                logger.warning(f"Error listing SC products: {e}")
                break

        return products
