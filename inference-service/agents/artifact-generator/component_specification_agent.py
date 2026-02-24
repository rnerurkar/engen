"""
ComponentSpecificationAgent — Real-Time Source Edition

Agent wrapper around ComponentSpecification core logic.
Maintains the same process(req) -> AgentResponse interface so
that main.py / UnifiedArtifactAgent can invoke it without changes.

Now uses real-time GitHub MCP + AWS Service Catalog lookups instead
of the VertexAI Search index populated by component_catalog_pipeline.py.
"""

import os
import logging
from typing import Optional, List

from core.pattern_synthesis.component_specification import ComponentSpecification
from config import Config
from lib.adk_core import AgentRequest, AgentResponse, TaskStatus

logger = logging.getLogger(__name__)


def _get_github_repos() -> List[str]:
    """Load GitHub repos to search from env or config."""
    env_repos = os.getenv("GITHUB_TERRAFORM_REPOS", "")
    if env_repos:
        return [r.strip() for r in env_repos.split(",") if r.strip()]
    try:
        from lib.component_sources import GITHUB_TERRAFORM_REPOS
        return GITHUB_TERRAFORM_REPOS
    except ImportError:
        return []


class ComponentSpecificationAgent:
    """
    Agent wrapper around ComponentSpecification core logic.

    Two-tier real-time lookup strategy:
      Tier 1: GitHub MCP Server → Terraform modules
      Tier 2: AWS Service Catalog (Boto3) → SC Products

    Falls back gracefully if GitHub MCP / Service Catalog are unavailable.
    """

    def __init__(self, mcp_session=None):
        """
        Args:
            mcp_session: Optional active MCP session (GitHub MCP Server).
                         If None, falls back to PyGithub or skips GH lookup.
        """
        github_repos = _get_github_repos()
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        aws_profile = os.getenv("AWS_PROFILE") or None

        self.engine = ComponentSpecification(
            project_id=Config.PROJECT_ID,
            mcp_session=mcp_session,
            github_org_repos=github_repos,
            aws_region=aws_region,
            aws_profile=aws_profile,
        )

    def process(self, req: AgentRequest) -> AgentResponse:
        """
        Process an AgentRequest to extract component specifications.

        Expected payload keys:
            documentation (str): The pattern / architecture documentation text.

        Returns:
            AgentResponse with specifications and execution_plan on success.
        """
        documentation = req.payload.get("documentation")
        if not documentation:
            return AgentResponse(
                status=TaskStatus.FAILED,
                error="Missing 'documentation' in payload",
                agent_name="ComponentSpecificationAgent",
            )

        try:
            specs = self.engine.process_documentation(documentation)

            if "error" in specs:
                return AgentResponse(
                    status=TaskStatus.FAILED,
                    error=specs["error"],
                    agent_name="ComponentSpecificationAgent",
                )

            return AgentResponse(
                status=TaskStatus.COMPLETED,
                result={
                    "specifications": specs,
                    "execution_plan": specs.get("execution_order", []),
                },
                agent_name="ComponentSpecificationAgent",
            )
        except Exception as e:
            logger.error(f"Error in ComponentSpecificationAgent: {e}", exc_info=True)
            return AgentResponse(
                status=TaskStatus.FAILED,
                error=str(e),
                agent_name="ComponentSpecificationAgent",
            )
