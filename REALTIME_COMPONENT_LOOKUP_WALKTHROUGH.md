# Real-Time Component Lookup — A Plain English Walkthrough

When the Pattern Factory generates infrastructure code (Terraform files, CloudFormation templates), it needs to know the *exact* input parameters that each cloud resource accepts. For example: "What variables does our company's Terraform module for an S3 bucket expect? Does it need `bucket_name`? `versioning_enabled`? What are the defaults?"

If the agent guesses wrong, it generates code that won't compile or deploy. So we need a **source of truth** — a way to look up the real schema of every infrastructure component.

This document explains how that lookup works, using two systems: the **GitHub MCP Server** for Terraform modules, and the **AWS Service Catalog SDK (boto3)** for CloudFormation products.

---

## Why Not Pre-Index Everything? (The Old Way vs. The New Way)

### The Old Way (Legacy Pipeline — Retired in v2.0)

There used to be an **offline batch pipeline** (`component_catalog_pipeline_legacy.py`) that ran periodically, scanned a GitHub repo for Terraform modules, queried AWS Service Catalog for products, and indexed all their schemas into Vertex AI Search.

The agents would then search that index at runtime — essentially a cached copy of the schemas.

**Problems:**
- **Stale data** — If someone pushed a new Terraform module to GitHub, the agents wouldn't know about it until the pipeline ran again (maybe overnight or weekly).
- **Limited scope** — Only modules in pre-configured repos were indexed.
- **Extra infrastructure** — A whole separate pipeline to run, monitor, and maintain.

### The New Way (Real-Time Lookup — v2.0+)

Now, when the **Component Specification Agent** needs a schema, it queries GitHub and AWS Service Catalog **live, at that moment.** No pre-indexing, no stale data, no separate pipeline.

This is like the difference between looking up a word in a printed dictionary (which might be outdated) versus searching the internet (which always has the latest information).

---

## How the Lookup Works — End to End

### Step 1 — Extract Keywords from the Documentation

The Component Specification Agent feeds the pattern documentation to **Gemini 1.5 Pro** and asks it to identify 5–10 keywords representing the infrastructure components (e.g., "postgres", "vpc", "fargate", "lambda", "s3").

### Step 2 — Normalize the Keywords

Raw keywords from the AI can be messy — "postgres", "postgresql", "database", "rds" all mean the same thing. The **`component_sources.py`** module has a dictionary of **40+ aliases** that maps them all to a canonical type:

| Raw Keyword | Canonical Type |
|------------|---------------|
| postgres, postgresql, mysql, aurora, database, rds | `rds_instance` |
| lambda, function, serverless_function | `lambda_function` |
| k8s, kubernetes, eks | `eks_cluster` |
| redis, memcached, cache, elasticache | `elasticache` |
| alb, elb, nlb, load_balancer | `load_balancer` |

This normalization ensures that no matter what the AI calls the component, the system searches for the right thing.

### Step 3 — Tier 1: Search GitHub for Terraform Modules

For each canonical component type, the system first tries to find a matching **Terraform module** in the company's GitHub repositories.

**Which repos are searched?** Configured via the `GITHUB_TERRAFORM_REPOS` environment variable (comma-separated list of `org/repo` names). Default: `rnerurkar/engen-infrastructure`.

The lookup happens through the **`GitHubMCPTerraformClient`** (`inference-service/lib/github_mcp_client.py`), which has two modes:

#### Mode A — GitHub MCP Server (Primary)

If an MCP session is available (more on this in the [MCP Setup Guide](GITHUB_MCP_SETUP_WALKTHROUGH.md)), the client calls MCP tools:

1. **`search_code`** — Searches the repo for files named `variables.tf` that match the component pattern (e.g., `filename:variables.tf s3 repo:myorg/tf-modules`). This is GitHub's code search, exposed through MCP.

2. **`get_file_contents`** — Reads the actual content of `variables.tf` and `outputs.tf` from the matching module directory.

3. **`search_repositories`** — If no match is found in the configured repos, searches across the entire GitHub organization for repos named like `terraform-{pattern}` (e.g., `terraform-s3`, `terraform-rds`).

The MCP client parses the returned HCL (HashiCorp Configuration Language) content to extract every variable's name, type, description, and default value, plus every output's name and value expression.

#### Mode B — PyGithub REST API (Fallback)

If MCP is not available (e.g., MCP server not running, or agents deployed without MCP support), the client automatically falls back to **PyGithub**, a Python library that talks directly to the GitHub REST API:

1. Connects to the repo using a GitHub Personal Access Token (`GITHUB_TOKEN` env var).
2. Walks the `modules/` directory tree.
3. For each subdirectory whose name matches the search pattern (e.g., directory named "s3" for an `s3_bucket` lookup), reads `variables.tf`, `outputs.tf`, and `README.md`.
4. Parses the HCL content using `python-hcl2` (with a regex fallback if `hcl2` parsing fails).

#### What Gets Returned

Both modes produce a **`TerraformModuleSpec`** dataclass containing:
- **module_name** — e.g., "terraform-s3-bucket"
- **source_repo** — e.g., "myorg/terraform-modules"
- **source_path** — e.g., "modules/s3"
- **variables** — List of `TerraformVariable` objects (name, type, description, default, required flag)
- **outputs** — List of `TerraformOutput` objects (name, description, value expression)
- **found_via** — Either `"github_mcp"` or `"github_pygithub"` so you can tell which path was used

This gets converted to a **catalog schema** (a JSON dictionary) that the LLM can read and use to generate accurate Terraform code.

### Step 4 — Tier 2: Search AWS Service Catalog (Fallback)

If GitHub doesn't have a matching Terraform module, the system falls back to **AWS Service Catalog** — a managed AWS service where the company pre-registers approved CloudFormation products.

The lookup happens through the **`ServiceCatalogClient`** (`inference-service/lib/service_catalog_client.py`), which uses **boto3** (the official AWS SDK for Python):

1. **Search for products** — Calls `search_products()` with a full-text search filter (e.g., "S3", "RDS", "Lambda"). Like the Terraform client, it has a mapping of component types to search terms.

2. **Find the latest version** — For each matching product, calls `list_provisioning_artifacts()` and sorts by creation date to find the most recent, non-deprecated version.

3. **Extract parameters** — Calls `describe_provisioning_parameters()` for the latest version. This returns every input parameter the product needs, including:
   - Parameter key (name)
   - Type (String, Number, etc.)
   - Description
   - Default value
   - Allowed values (dropdown choices)
   - Constraints (min/max length, regex patterns)
   - IsNoEcho flag (for secrets like passwords)

4. **Cache results** — To avoid making the same AWS API call twice, results are cached in memory for the duration of the session.

#### What Gets Returned

A **`ServiceCatalogProductSpec`** dataclass containing:
- **product_id** and **product_name** — From the Service Catalog
- **provisioning_artifact_id** — The specific version to deploy
- **parameters** — List of `ServiceCatalogParameter` objects with all constraints
- **found_via** — Always `"service_catalog_boto3"`

This also gets converted to a catalog schema JSON.

### Step 5 — Feed Everything to the LLM

All the schemas found (from both GitHub and Service Catalog) are concatenated into a single text block and included in the LLM prompt. The prompt tells Gemini 1.5 Pro:

> "Here are the actual interface definitions of the infrastructure components available. Use these exact variable names, types, and defaults when generating the component specification. If a component matches a `terraform_module`, set its type to `terraform_module` and use the variable names from the catalog. If it matches a `service_catalog_product`, set its type to `service_catalog_product` and copy the `product_id` and `artifact_id`."

This is what **grounds** the generated code in reality — the AI can't hallucinate variable names that don't exist because it has the real schema right in front of it.

### Step 6 — Build the Dependency Graph

The LLM returns a JSON specification with all components and their dependencies. The system then runs a **topological sort** (using Python's built-in `graphlib.TopologicalSorter`) to determine the correct provisioning order.

For example, if the pattern has a VPC, an ECS cluster, and an RDS database:
- VPC must be created first (no dependencies)
- ECS cluster depends on VPC (needs `vpc_id` and `subnet_ids`)
- RDS database depends on VPC (needs `security_group_ids`)

The topological sort produces: `VPC → RDS → ECS` (or `VPC → ECS → RDS` — both are valid since RDS and ECS only depend on VPC, not on each other).

---

## Configuration Reference

| Setting | Environment Variable | Default | Purpose |
|---------|---------------------|---------|---------|
| GitHub repos to search | `GITHUB_TERRAFORM_REPOS` | `rnerurkar/engen-infrastructure` | Comma-separated list of `org/repo` |
| GitHub access token | `GITHUB_TOKEN` | *(required)* | For MCP authentication and PyGithub fallback |
| AWS region | `AWS_REGION` | `us-east-1` | Where Service Catalog products live |
| AWS profile | `AWS_PROFILE` | `default` | Which AWS credentials profile to use |

---

## Summary: The Two-Tier Lookup Strategy

```
Component Specification Agent needs schema for "rds_instance"
    │
    ├── Tier 1: GitHub MCP Client
    │   ├── MCP session available? → Use MCP tools (search_code, get_file_contents)
    │   └── No MCP session? → Use PyGithub REST API (walk repo tree)
    │   └── Found? → Return TerraformModuleSpec ✓
    │
    └── Tier 2: AWS Service Catalog Client (only if Tier 1 found nothing)
        └── boto3 → search_products → describe_provisioning_parameters
        └── Found? → Return ServiceCatalogProductSpec ✓

    If neither tier finds anything → Agent proceeds without authoritative schema
    (LLM generates best-effort spec based on documentation alone)
```
