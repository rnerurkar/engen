"""
GitHub MCP Client for Terraform Module Discovery.

Uses GitHub MCP Server to search for and extract Terraform modules
from GitHub repositories in real-time, replacing the offline
component_catalog_pipeline ingestion into VertexAI Search.
"""

import json
import re
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class TerraformVariable:
    """Represents a Terraform input variable."""
    name: str
    type: str = "string"
    description: str = ""
    default: Optional[Any] = None
    required: bool = True
    validation: Optional[Dict[str, Any]] = None


@dataclass
class TerraformOutput:
    """Represents a Terraform output."""
    name: str
    description: str = ""
    value_expression: str = ""


@dataclass
class TerraformModuleSpec:
    """Extracted specification from a Terraform module."""
    module_name: str
    source_repo: str
    source_path: str
    description: str = ""
    variables: List[TerraformVariable] = field(default_factory=list)
    outputs: List[TerraformOutput] = field(default_factory=list)
    provider: str = "aws"
    version: str = "latest"
    found_via: str = "github_mcp"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_catalog_schema(self) -> Dict[str, Any]:
        """Convert to the schema format expected by the ComponentSpecification engine."""
        attributes = {}
        for var in self.variables:
            attributes[var.name] = {
                "type": var.type,
                "description": var.description,
                "default": var.default if var.default is not None else "<<REQUIRED>>",
                "required": var.required,
            }
        return {
            "type": "terraform_module",
            "source": f"{self.source_repo}/{self.source_path}",
            "module_name": self.module_name,
            "provider": self.provider,
            "description": self.description,
            "attributes": attributes,
            "outputs": {
                out.name: {
                    "description": out.description,
                    "value_expression": out.value_expression,
                }
                for out in self.outputs
            },
        }


class GitHubMCPTerraformClient:
    """
    Client that uses GitHub MCP Server tools to discover and extract
    Terraform module specifications from GitHub repositories.

    This replaces the offline ingestion pipeline with real-time
    module discovery.

    Usage with MCP session:
        client = GitHubMCPTerraformClient(mcp_session, org_repos=["myorg/tf-modules"])
        spec = await client.search_terraform_module("s3_bucket")

    Usage without MCP session (direct GitHub API via PyGithub):
        client = GitHubMCPTerraformClient(mcp_session=None, org_repos=["myorg/tf-modules"])
        spec = await client.search_terraform_module("s3_bucket")
    """

    # Mapping of component types to likely Terraform module name patterns
    COMPONENT_TO_MODULE_PATTERNS: Dict[str, List[str]] = {
        "s3_bucket": ["s3", "bucket", "storage"],
        "lambda_function": ["lambda", "function", "serverless"],
        "api_gateway": ["api-gateway", "apigateway", "api_gateway"],
        "dynamodb_table": ["dynamodb", "dynamo", "nosql"],
        "ecs_service": ["ecs", "container", "fargate"],
        "eks_cluster": ["eks", "kubernetes", "k8s"],
        "rds_instance": ["rds", "database", "postgres", "mysql", "aurora"],
        "sqs_queue": ["sqs", "queue", "messaging"],
        "sns_topic": ["sns", "topic", "notification"],
        "vpc": ["vpc", "network", "networking"],
        "cloudfront": ["cloudfront", "cdn", "distribution"],
        "elasticache": ["elasticache", "redis", "memcached", "cache"],
        "iam_role": ["iam", "role", "permission"],
        "waf": ["waf", "firewall", "web-acl"],
        "kms_key": ["kms", "key", "encryption"],
        "secrets_manager": ["secrets", "secretsmanager", "secret"],
        "step_function": ["step-function", "sfn", "state-machine"],
        "codepipeline": ["codepipeline", "pipeline", "cicd"],
        "ecr_repository": ["ecr", "container-registry", "registry"],
        "load_balancer": ["alb", "elb", "load-balancer", "nlb"],
    }

    def __init__(
        self,
        mcp_session: Optional[Any] = None,
        org_repos: Optional[List[str]] = None,
        github_token: Optional[str] = None,
    ):
        """
        Args:
            mcp_session: Active MCP session connected to GitHub MCP Server.
                         If None, falls back to PyGithub direct API access.
            org_repos: List of GitHub orgs/repos to search.
                       e.g., ["myorg/terraform-modules", "myorg/infra-modules"]
            github_token: GitHub PAT. Defaults to GITHUB_TOKEN env var.
        """
        self.mcp_session = mcp_session
        self.org_repos = org_repos or []
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self._github_client = None  # lazy-initialized PyGithub client

    @property
    def github_client(self):
        """Lazy-initialize PyGithub client for non-MCP fallback."""
        if self._github_client is None:
            try:
                from github import Github
                self._github_client = Github(self.github_token) if self.github_token else Github()
            except ImportError:
                logger.warning("PyGithub not installed. Install with: pip install PyGithub")
                self._github_client = None
        return self._github_client

    async def search_terraform_module(
        self, component_type: str, component_name: str = ""
    ) -> Optional[TerraformModuleSpec]:
        """
        Search for a Terraform module matching the component type.

        Tries:
          1. GitHub MCP Server tools (if session available)
          2. Direct PyGithub API (fallback)

        Args:
            component_type: The type of infrastructure component (e.g., "s3_bucket")
            component_name: Optional specific name for more targeted search

        Returns:
            TerraformModuleSpec if found, None otherwise
        """
        patterns = self.COMPONENT_TO_MODULE_PATTERNS.get(
            component_type.lower(), [component_type]
        )

        if self.mcp_session:
            return await self._search_via_mcp(patterns, component_type)
        else:
            return await self._search_via_pygithub(patterns, component_type)

    # ─── MCP-based search ────────────────────────────────────────────────

    async def _search_via_mcp(
        self, patterns: List[str], component_type: str
    ) -> Optional[TerraformModuleSpec]:
        """Search using GitHub MCP Server tools."""
        for repo in self.org_repos:
            for pattern in patterns:
                spec = await self._mcp_search_in_repo(repo, pattern, component_type)
                if spec:
                    return spec

        # Broader org-level search
        spec = await self._mcp_search_across_org(patterns, component_type)
        return spec

    async def _mcp_search_in_repo(
        self, repo: str, pattern: str, component_type: str
    ) -> Optional[TerraformModuleSpec]:
        """Search a specific repo using MCP search_code tool."""
        try:
            search_result = await self.mcp_session.call_tool(
                "search_code",
                {
                    "q": f"filename:variables.tf {pattern} repo:{repo}",
                    "per_page": 5,
                },
            )
            if not search_result or not search_result.content:
                return None

            items = self._parse_mcp_json_result(search_result, "items")
            for item in items:
                file_path = item.get("path", "")
                module_dir = "/".join(file_path.split("/")[:-1])
                spec = await self._mcp_extract_module_spec(repo, module_dir, component_type)
                if spec:
                    return spec
        except Exception as e:
            logger.debug(f"MCP search_code in {repo} for '{pattern}': {e}")
        return None

    async def _mcp_search_across_org(
        self, patterns: List[str], component_type: str
    ) -> Optional[TerraformModuleSpec]:
        """Search across org for Terraform module repos via MCP."""
        try:
            for pattern in patterns:
                search_result = await self.mcp_session.call_tool(
                    "search_repositories",
                    {
                        "query": f"terraform-{pattern} in:name language:HCL",
                        "per_page": 5,
                    },
                )
                if not search_result or not search_result.content:
                    continue

                repos = self._parse_mcp_json_result(search_result, "items")
                for repo_info in repos:
                    repo_full_name = repo_info.get("full_name", "")
                    spec = await self._mcp_extract_module_spec(
                        repo_full_name, "", component_type
                    )
                    if spec:
                        return spec
        except Exception as e:
            logger.debug(f"MCP org search for {component_type}: {e}")
        return None

    async def _mcp_extract_module_spec(
        self, repo: str, module_path: str, component_type: str
    ) -> Optional[TerraformModuleSpec]:
        """Extract full TF module spec by reading files via MCP get_file_contents."""
        owner, repo_name = repo.split("/", 1)
        base_path = f"{module_path}/" if module_path else ""

        # Read variables.tf (required)
        try:
            var_result = await self.mcp_session.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo_name, "path": f"{base_path}variables.tf"},
            )
            if not var_result or not var_result.content:
                return None
            var_content = self._extract_mcp_text(var_result)
            variables = self._parse_variables_tf(var_content)
        except Exception:
            return None

        # Read outputs.tf (optional)
        outputs: List[TerraformOutput] = []
        try:
            out_result = await self.mcp_session.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo_name, "path": f"{base_path}outputs.tf"},
            )
            if out_result and out_result.content:
                out_content = self._extract_mcp_text(out_result)
                outputs = self._parse_outputs_tf(out_content)
        except Exception:
            pass

        # Read README.md for description (optional)
        description = ""
        try:
            readme_result = await self.mcp_session.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo_name, "path": f"{base_path}README.md"},
            )
            if readme_result and readme_result.content:
                readme_content = self._extract_mcp_text(readme_result)
                for line in readme_content.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        description = line
                        break
        except Exception:
            pass

        if not variables:
            return None

        return TerraformModuleSpec(
            module_name=f"terraform-{component_type}",
            source_repo=repo,
            source_path=module_path or "/",
            description=description,
            variables=variables,
            outputs=outputs,
            provider="aws",
            found_via="github_mcp",
        )

    # ─── PyGithub-based fallback search ──────────────────────────────────

    async def _search_via_pygithub(
        self, patterns: List[str], component_type: str
    ) -> Optional[TerraformModuleSpec]:
        """Fallback search using PyGithub when MCP session is unavailable."""
        if not self.github_client:
            logger.warning("No GitHub client available (no MCP session and PyGithub not installed).")
            return None

        for repo_name in self.org_repos:
            try:
                repo = self.github_client.get_repo(repo_name)
                spec = self._pygithub_scan_repo(repo, patterns, component_type)
                if spec:
                    return spec
            except Exception as e:
                logger.debug(f"PyGithub scan of {repo_name}: {e}")
        return None

    def _pygithub_scan_repo(
        self, repo: Any, patterns: List[str], component_type: str
    ) -> Optional[TerraformModuleSpec]:
        """Scan a PyGithub Repository object for matching TF modules."""
        import base64

        try:
            contents = repo.get_contents("modules")
        except Exception:
            try:
                contents = repo.get_contents("")
            except Exception:
                return None

        # Walk directory tree looking for variables.tf in matching dirs
        while contents:
            item = contents.pop(0)
            if item.type == "dir":
                dir_name = item.name.lower()
                if any(p.lower() in dir_name for p in patterns):
                    # This dir matches a pattern – look for variables.tf
                    try:
                        sub = repo.get_contents(item.path)
                        var_file = next((f for f in sub if f.name == "variables.tf"), None)
                        if var_file:
                            var_content = base64.b64decode(var_file.content).decode("utf-8")
                            variables = self._parse_variables_tf(var_content)
                            if not variables:
                                continue

                            outputs: List[TerraformOutput] = []
                            out_file = next((f for f in sub if f.name == "outputs.tf"), None)
                            if out_file:
                                out_content = base64.b64decode(out_file.content).decode("utf-8")
                                outputs = self._parse_outputs_tf(out_content)

                            description = ""
                            readme_file = next((f for f in sub if f.name.lower() == "readme.md"), None)
                            if readme_file:
                                readme_text = base64.b64decode(readme_file.content).decode("utf-8")
                                for line in readme_text.strip().split("\n"):
                                    line = line.strip()
                                    if line and not line.startswith("#"):
                                        description = line
                                        break

                            return TerraformModuleSpec(
                                module_name=item.name,
                                source_repo=repo.full_name,
                                source_path=item.path,
                                description=description,
                                variables=variables,
                                outputs=outputs,
                                provider="aws",
                                found_via="github_pygithub",
                            )
                    except Exception as e:
                        logger.debug(f"Error scanning {item.path}: {e}")
                else:
                    # Not a match, but keep walking
                    try:
                        contents.extend(repo.get_contents(item.path))
                    except Exception:
                        pass
        return None

    # ─── HCL Parsing Helpers ─────────────────────────────────────────────

    @staticmethod
    def _parse_variables_tf(content: str) -> List[TerraformVariable]:
        """Parse variables.tf HCL content to extract variable definitions."""
        variables: List[TerraformVariable] = []

        # Try python-hcl2 first for reliable parsing
        try:
            import hcl2
            import io
            parsed = hcl2.load(io.StringIO(content))
            for entry in parsed.get("variable", []):
                for name, config in entry.items():
                    var_type = str(config.get("type", "string"))
                    desc = config.get("description", "")
                    default = config.get("default")
                    required = default is None
                    variables.append(
                        TerraformVariable(
                            name=name,
                            type=var_type,
                            description=desc,
                            default=default,
                            required=required,
                        )
                    )
            return variables
        except ImportError:
            logger.debug("python-hcl2 not available; falling back to regex parsing.")
        except Exception as e:
            logger.debug(f"hcl2 parse failed ({e}); falling back to regex.")

        # Regex fallback
        var_pattern = re.compile(
            r'variable\s+"([^"]+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
            re.MULTILINE | re.DOTALL,
        )
        for match in var_pattern.finditer(content):
            var_name = match.group(1)
            var_body = match.group(2)

            type_match = re.search(r'type\s*=\s*(\S+(?:\([^)]*\))?)', var_body)
            var_type = type_match.group(1) if type_match else "string"

            desc_match = re.search(r'description\s*=\s*"([^"]*)"', var_body)
            var_desc = desc_match.group(1) if desc_match else ""

            default_match = re.search(r'default\s*=\s*(.+)', var_body)
            var_default = None
            required = True
            if default_match:
                var_default = default_match.group(1).strip()
                required = False

            variables.append(
                TerraformVariable(
                    name=var_name,
                    type=var_type,
                    description=var_desc,
                    default=var_default,
                    required=required,
                )
            )
        return variables

    @staticmethod
    def _parse_outputs_tf(content: str) -> List[TerraformOutput]:
        """Parse outputs.tf HCL content to extract output definitions."""
        outputs: List[TerraformOutput] = []

        # Try python-hcl2 first
        try:
            import hcl2
            import io
            parsed = hcl2.load(io.StringIO(content))
            for entry in parsed.get("output", []):
                for name, config in entry.items():
                    desc = config.get("description", "")
                    value_expr = str(config.get("value", ""))
                    outputs.append(
                        TerraformOutput(name=name, description=desc, value_expression=value_expr)
                    )
            return outputs
        except ImportError:
            pass
        except Exception:
            pass

        # Regex fallback
        output_pattern = re.compile(
            r'output\s+"([^"]+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
            re.MULTILINE | re.DOTALL,
        )
        for match in output_pattern.finditer(content):
            out_name = match.group(1)
            out_body = match.group(2)

            desc_match = re.search(r'description\s*=\s*"([^"]*)"', out_body)
            out_desc = desc_match.group(1) if desc_match else ""

            value_match = re.search(r'value\s*=\s*(.+)', out_body)
            value_expr = value_match.group(1).strip() if value_match else ""

            outputs.append(
                TerraformOutput(name=out_name, description=out_desc, value_expression=value_expr)
            )
        return outputs

    # ─── MCP result parsing helpers ──────────────────────────────────────

    @staticmethod
    def _parse_mcp_json_result(result: Any, key: str) -> List[Dict[str, Any]]:
        """Parse an MCP tool result containing JSON with a top-level key."""
        try:
            text = GitHubMCPTerraformClient._extract_mcp_text(result)
            data = json.loads(text)
            return data.get(key, [])
        except (json.JSONDecodeError, AttributeError):
            return []

    @staticmethod
    def _extract_mcp_text(result: Any) -> str:
        """Extract text content from an MCP tool result."""
        if hasattr(result, "content"):
            for block in result.content:
                if hasattr(block, "text"):
                    return block.text
        return ""
