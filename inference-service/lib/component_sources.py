"""
Configuration for real-time component source discovery.

Replaces the pipeline-based catalog configuration that was used by
component_catalog_pipeline.py and the VertexAI Search data store.
"""

import os
from typing import Dict, List

# ─── GitHub repositories to search for Terraform modules ─────────────────
# Searched in order; first match wins.
# Override via env var GITHUB_TERRAFORM_REPOS (comma-separated).

GITHUB_TERRAFORM_REPOS: List[str] = [
    r.strip()
    for r in os.getenv(
        "GITHUB_TERRAFORM_REPOS",
        "rnerurkar/engen-infrastructure",
    ).split(",")
    if r.strip()
]

# ─── AWS Service Catalog configuration ───────────────────────────────────

AWS_SERVICE_CATALOG = {
    "region": os.getenv("AWS_REGION", "us-east-1"),
    "profile": os.getenv("AWS_PROFILE") or None,
}

# ─── Component type normalisation mapping ────────────────────────────────
# Maps various component names found in pattern docs to canonical types.

COMPONENT_TYPE_ALIASES: Dict[str, str] = {
    # Storage
    "s3": "s3_bucket",
    "bucket": "s3_bucket",
    "object_storage": "s3_bucket",
    # Compute
    "lambda": "lambda_function",
    "function": "lambda_function",
    "serverless_function": "lambda_function",
    # API
    "api": "api_gateway",
    "rest_api": "api_gateway",
    "http_api": "api_gateway",
    # Database – NoSQL
    "dynamodb": "dynamodb_table",
    "nosql": "dynamodb_table",
    # Database – Relational
    "rds": "rds_instance",
    "database": "rds_instance",
    "postgres": "rds_instance",
    "postgresql": "rds_instance",
    "mysql": "rds_instance",
    "aurora": "rds_instance",
    # Container
    "ecs": "ecs_service",
    "fargate": "ecs_service",
    "container": "ecs_service",
    "eks": "eks_cluster",
    "kubernetes": "eks_cluster",
    "k8s": "eks_cluster",
    # Messaging
    "sqs": "sqs_queue",
    "queue": "sqs_queue",
    "sns": "sns_topic",
    "topic": "sns_topic",
    "notification": "sns_topic",
    # Networking
    "vpc": "vpc",
    "network": "vpc",
    "cloudfront": "cloudfront",
    "cdn": "cloudfront",
    "alb": "load_balancer",
    "elb": "load_balancer",
    "nlb": "load_balancer",
    "load_balancer": "load_balancer",
    # Cache
    "elasticache": "elasticache",
    "redis": "elasticache",
    "memcached": "elasticache",
    "cache": "elasticache",
    # Security
    "iam": "iam_role",
    "role": "iam_role",
    "waf": "waf",
    "firewall": "waf",
    "kms": "kms_key",
    "encryption": "kms_key",
    "secrets": "secrets_manager",
    "secret": "secrets_manager",
    # CI/CD
    "pipeline": "codepipeline",
    "cicd": "codepipeline",
    "ecr": "ecr_repository",
    "container_registry": "ecr_repository",
    # Orchestration
    "step_function": "step_function",
    "step_functions": "step_function",
    "state_machine": "step_function",
    "workflow": "step_function",
}


def normalize_component_type(raw_type: str) -> str:
    """Normalise a component type from pattern docs to its canonical form."""
    normalised = raw_type.lower().strip().replace("-", "_").replace(" ", "_")
    return COMPONENT_TYPE_ALIASES.get(normalised, normalised)
