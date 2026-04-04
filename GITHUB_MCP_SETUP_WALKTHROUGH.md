# GitHub MCP Server Setup — A Plain English Walkthrough

This document explains what the **GitHub MCP Server** is, why EnGen uses it, and exactly how to set it up for two scenarios: running agents **locally on your laptop** versus running them **remotely on Vertex AI Agent Engine** in a GCP project.

---

## What Is MCP?

**MCP** stands for **Model Context Protocol**. It's an open standard (created by Anthropic) that lets AI agents talk to external tools and data sources through a simple, standardized interface.

Think of it like a **universal adapter** between AI agents and the outside world. Instead of every agent writing custom code to call the GitHub API, the Slack API, the Jira API, etc., MCP defines a common "language" that any agent can speak, and each external service provides an **MCP Server** that translates that language into its own API calls.

### The Key Players

| Concept | What it is | Example |
|---------|-----------|---------|
| **MCP Host** | The application that runs the agent | Your Python app, or Vertex AI Agent Engine |
| **MCP Client** | A component inside the host that maintains a connection to MCP Servers | The `mcp_session` object in our code |
| **MCP Server** | A lightweight program that exposes a specific service's capabilities as "tools" | GitHub MCP Server, Google Drive MCP Server, etc. |
| **Tools** | Individual actions the server can perform | `search_code`, `get_file_contents`, `create_pull_request` |

### Why Not Just Use the GitHub REST API Directly?

You could — and in fact, EnGen's `GitHubMCPTerraformClient` has a **PyGithub fallback** for exactly this reason. But MCP offers key advantages:

1. **Standardization** — The agent's code doesn't change if you swap GitHub for GitLab. You just swap the MCP Server.
2. **Authentication delegation** — The MCP Server handles tokens and OAuth flows. The agent never sees credentials directly.
3. **Tool discovery** — The agent can ask the MCP Server "what tools do you have?" and dynamically discover capabilities at runtime.
4. **Framework integration** — Google's ADK (Agent Development Kit) has built-in MCP support via `MCPToolset`, which automatically converts MCP tools into agent-callable functions.

---

## What Tools Does the GitHub MCP Server Provide?

GitHub's official MCP Server (published as `@modelcontextprotocol/server-github`) exposes these tools that EnGen uses:

| Tool | What It Does | How EnGen Uses It |
|------|-------------|-------------------|
| `search_code` | Searches for code across GitHub repositories | Find `variables.tf` files matching a component type |
| `search_repositories` | Searches for repositories by name/topic | Find repos named `terraform-{component}` across the org |
| `get_file_contents` | Reads a specific file from a repo | Read the actual content of `variables.tf`, `outputs.tf`, `README.md` |
| `create_or_update_file` | Creates or updates a file in a repo | Used by the GitHub Publisher to push generated code |
| `push_files` | Pushes multiple files in a single commit | Batch publishing of generated artifacts |

---

## Setup Option 1: Local Development (Your Laptop)

When you run agents locally (e.g., via `python -m google.adk web` or a simple Python script), the GitHub MCP Server runs as a **child process** on your machine, communicating with your agent over **stdio** (standard input/output pipes).

### How It Works

```
┌─────────────────────────────────────────────┐
│  Your Laptop                                │
│                                             │
│  ┌───────────────┐    stdio    ┌─────────┐  │
│  │  Python Agent  │◄──────────►│ GitHub  │  │
│  │  (MCP Client)  │  (pipes)   │  MCP    │  │
│  │               │            │ Server  │  │
│  └───────────────┘            │ (Node)  │  │
│                               └────┬────┘  │
│                                    │       │
└────────────────────────────────────┼───────┘
                                     │ HTTPS
                                     ▼
                              GitHub API (github.com)
```

### Step-by-Step Setup

#### Prerequisites

1. **Node.js** (v18 or later) — The GitHub MCP Server is a Node.js application.
   ```powershell
   # Check if installed
   node --version
   
   # If not, install via winget (Windows) or brew (Mac)
   winget install OpenJS.NodeJS.LTS
   ```

2. **npx** — Comes bundled with Node.js. Used to run the MCP server without installing it globally.
   ```powershell
   npx --version
   ```

3. **GitHub Personal Access Token (PAT)** — The MCP server needs this to authenticate with GitHub's API.
   - Go to [github.com/settings/tokens](https://github.com/settings/tokens)
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (full control of private repos) and `read:org` (read org membership)
   - Copy the token — you'll need it in the next step

#### Configuration

Set your GitHub token as an environment variable:

```powershell
# PowerShell (current session)
$env:GITHUB_TOKEN = "ghp_your_token_here"

# Or permanently via system environment variables
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_your_token_here", "User")
```

#### Option A: Using Google ADK's Built-In MCP Support

If you're using Google's ADK framework (which EnGen is built on), you can wire the MCP Server directly into your agent definition. The ADK handles starting the server process and maintaining the session automatically.

In your agent's `__init__.py` or `agent.py`, you would configure the MCP toolset like this:

```python
from google.adk.toolsets import MCPToolset
from mcp import StdioServerParameters

# Define how to start the GitHub MCP Server
github_mcp_server = StdioServerParameters(
    command="npx",
    args=[
        "-y", 
        "@modelcontextprotocol/server-github"
    ],
    env={
        "GITHUB_PERSONAL_ACCESS_TOKEN": os.environ["GITHUB_TOKEN"]
    }
)

# Create the toolset — ADK will start the server and manage the session
github_tools = MCPToolset(server_params=github_mcp_server)

# Pass it to your agent
agent = LlmAgent(
    name="component_spec_agent",
    model="gemini-2.0-flash",
    tools=[github_tools],
    # ... other config
)
```

When the agent starts, ADK:
1. Spawns the GitHub MCP Server as a child process (runs `npx -y @modelcontextprotocol/server-github`)
2. Connects to it over stdio pipes
3. Discovers all available tools (`search_code`, `get_file_contents`, etc.)
4. Makes them available as callable functions in the agent's tool list
5. When the agent decides it needs to search GitHub, it calls the tool, and ADK routes the request to the MCP Server transparently

#### Option B: Manual MCP Session (Without ADK)

If you're not using ADK (or need more control), you can create an MCP session manually:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ["GITHUB_TOKEN"]}
)

# Start the server and get a session
async with stdio_client(server_params) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        
        # Now pass this session to our client
        from lib.github_mcp_client import GitHubMCPTerraformClient
        
        client = GitHubMCPTerraformClient(
            mcp_session=session,
            org_repos=["rnerurkar/engen-infrastructure"]
        )
        
        # Search for a Terraform module
        spec = await client.search_terraform_module("rds_instance")
```

#### Option C: No MCP at All (PyGithub Fallback)

If you don't want to deal with MCP setup during local development, you can skip it entirely. Just pass `mcp_session=None`:

```python
from lib.github_mcp_client import GitHubMCPTerraformClient

client = GitHubMCPTerraformClient(
    mcp_session=None,  # No MCP — will use PyGithub
    org_repos=["rnerurkar/engen-infrastructure"]
)

# This will automatically use PyGithub + GITHUB_TOKEN env var
spec = await client.search_terraform_module("rds_instance")
```

This is simpler to set up but loses the benefits of MCP (standardization, tool discovery, authentication delegation).

---

## Setup Option 2: Remote Deployment (Vertex AI Agent Engine on GCP)

When agents are deployed to **Vertex AI Agent Engine** (formerly called Reasoning Engine), they run inside a managed container on Google Cloud. The MCP setup is different because there's no "local laptop" to run a child process on.

### How It Works

```
┌──────────────────────────────────┐
│  Google Cloud Project            │
│                                  │
│  ┌──────────────────────────┐    │
│  │  Vertex AI Agent Engine  │    │
│  │  (Reasoning Engine)      │    │
│  │                          │    │
│  │  ┌────────────────────┐  │    │
│  │  │  Your Agent Code   │  │    │
│  │  │  (Python Package)  │  │    │
│  │  └────────┬───────────┘  │    │
│  │           │              │    │
│  │     ┌─────┴──────┐      │    │
│  │     │  MCP Client │      │    │
│  │     └─────┬──────┘      │    │
│  └───────────┼──────────────┘    │
│              │                   │
│    ┌─────────┴──────────┐       │
│    │  Option A: stdio   │       │
│    │  (npx bundled in   │       │
│    │   container image) │       │
│    └─────────┬──────────┘       │
│              │ OR               │
│    ┌─────────┴──────────┐       │
│    │  Option B: SSE/HTTP│       │
│    │  (Hosted MCP Server│       │
│    │   on Cloud Run)    │       │
│    └─────────┬──────────┘       │
└──────────────┼──────────────────┘
               │ HTTPS
               ▼
         GitHub API (github.com)
```

### Approach A: Bundle npx in the Container (Simpler)

This is the most straightforward approach. You include Node.js and the GitHub MCP Server in your agent's container image, and use the same `StdioServerParameters` approach as local development.

#### Step 1 — Add Node.js to Your Agent's Container

If deploying via Google ADK CLI (`adk deploy agent_engine`), you typically provide a `requirements.txt` and the ADK builds a container. To include Node.js, you need a custom Dockerfile:

```dockerfile
FROM python:3.11-slim

# Install Node.js (for GitHub MCP Server)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Pre-download the GitHub MCP Server so npx doesn't need to download it at runtime
RUN npx -y @modelcontextprotocol/server-github --help || true

# Copy agent code
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt

CMD ["python", "-m", "google.adk.cli", "serve"]
```

#### Step 2 — Configure MCP in Your Agent Code

The agent code is identical to the local setup — use `StdioServerParameters` with `npx`:

```python
github_mcp_server = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ["GITHUB_TOKEN"]}
)
```

#### Step 3 — Provide the GitHub Token as a Secret

In Agent Engine, you don't hardcode secrets. Instead, use **Google Secret Manager**:

1. Store your GitHub PAT in Secret Manager:
   ```bash
   echo -n "ghp_your_token" | gcloud secrets create github-token --data-file=-
   ```

2. Grant the Agent Engine service account access:
   ```bash
   gcloud secrets add-iam-policy-binding github-token \
     --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

3. In your agent code, read the secret at startup:
   ```python
   from google.cloud import secretmanager
   
   def get_github_token():
       client = secretmanager.SecretManagerServiceClient()
       name = f"projects/{PROJECT_ID}/secrets/github-token/versions/latest"
       response = client.access_secret_version(request={"name": name})
       return response.payload.data.decode("UTF-8")
   ```

### Approach B: Hosted MCP Server via SSE/HTTP (More Scalable)

Instead of bundling the MCP Server inside every agent container, you can run it as a **separate service** (e.g., on Cloud Run) and connect to it over **HTTP** using **SSE (Server-Sent Events)** or the newer **Streamable HTTP** transport.

#### Step 1 — Deploy the MCP Server to Cloud Run

Create a simple `Dockerfile` for the GitHub MCP Server:

```dockerfile
FROM node:20-slim
RUN npm install -g @modelcontextprotocol/server-github
EXPOSE 8080
CMD ["npx", "@modelcontextprotocol/server-github", "--transport", "sse", "--port", "8080"]
```

Deploy to Cloud Run:
```bash
gcloud run deploy github-mcp-server \
  --source . \
  --region us-central1 \
  --set-env-vars GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token \
  --allow-unauthenticated  # Or use IAM for auth
```

#### Step 2 — Connect Your Agent via SSE

In your agent code, switch from `StdioServerParameters` to `SseServerParameters`:

```python
from mcp.client.sse import SseServerParameters

github_mcp_server = SseServerParameters(
    url="https://github-mcp-server-XXXXX-uc.a.run.app/sse"
)
```

Or with the newer Streamable HTTP transport:

```python
from mcp.client.streamable_http import StreamableHttpParameters

github_mcp_server = StreamableHttpParameters(
    url="https://github-mcp-server-XXXXX-uc.a.run.app/mcp"
)
```

**Advantage:** Multiple agent instances share one MCP Server. No need for Node.js in every container. The MCP Server can scale independently.

**Disadvantage:** Network latency between agent and MCP Server. An extra service to manage.

### Approach C: PyGithub Fallback (Simplest for Agent Engine)

If MCP complexity isn't worth it for your use case, you can deploy agents to Agent Engine **without MCP** and rely entirely on the PyGithub fallback. This is what EnGen currently does for maximum compatibility:

```python
# In component_specification_agent.py
class ComponentSpecificationAgent:
    def __init__(self, mcp_session=None):
        # If mcp_session is None, the GitHub client will
        # automatically fall back to PyGithub REST API
        self.engine = ComponentSpecification(
            project_id=Config.PROJECT_ID,
            mcp_session=mcp_session,  # None on Agent Engine
            github_org_repos=_get_github_repos(),
            # ...
        )
```

This requires only `GITHUB_TOKEN` in the environment — no Node.js, no MCP Server, no extra infrastructure.

---

## The Decision Matrix: Which Approach When?

| Scenario | Recommended Approach | Why |
|----------|---------------------|-----|
| **Local development** (quick testing) | Option C — PyGithub fallback | Zero setup; just set `GITHUB_TOKEN` |
| **Local development** (full MCP experience) | Option A — stdio via `npx` | Easy; ADK manages the process lifecycle |
| **Agent Engine** (small scale, simple) | Approach C — PyGithub fallback | No Node.js needed; minimal infrastructure |
| **Agent Engine** (medium scale) | Approach A — Bundle npx in container | Same code as local; just add Node.js to Dockerfile |
| **Agent Engine** (large scale, multi-agent) | Approach B — Hosted MCP on Cloud Run | Shared server; independent scaling; no Node.js in agent containers |

---

## How EnGen's Code Handles All This

The `GitHubMCPTerraformClient` in `inference-service/lib/github_mcp_client.py` is designed to work in **any** of these scenarios without code changes:

```python
client = GitHubMCPTerraformClient(
    mcp_session=session_or_none,  # MCP session if available, None otherwise
    org_repos=["rnerurkar/engen-infrastructure"]
)

spec = await client.search_terraform_module("rds_instance")
```

Internally:
- If `mcp_session` is not `None` → Uses MCP tools (`search_code`, `get_file_contents`)
- If `mcp_session` is `None` → Falls back to PyGithub REST API
- If PyGithub isn't installed either → Returns `None` (graceful degradation)

The `ComponentSpecificationAgent` accepts an optional `mcp_session` in its constructor, which it passes through to the `GitHubMCPTerraformClient`. When deploying to Agent Engine, you either:
- Pass the MCP session from the ADK's `MCPToolset` (Approaches A/B)
- Pass `None` for the PyGithub fallback (Approach C)

---

## Deployment Cheat Sheet

### Local Development (Quick Start)

```powershell
# 1. Set your GitHub token
$env:GITHUB_TOKEN = "ghp_your_token_here"

# 2. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Run your agent
python -m google.adk web
```

### Agent Engine Deployment

```powershell
# 1. Store the GitHub token in Secret Manager
echo -n "ghp_your_token" | gcloud secrets create github-token --data-file=-

# 2. Set environment variables for the agent
# (These go in your Agent Engine configuration)
# GITHUB_TOKEN = fetched from Secret Manager at startup
# GITHUB_TERRAFORM_REPOS = "rnerurkar/engen-infrastructure"
# AWS_REGION = "us-east-1"

# 3. Deploy via ADK CLI
python deploy_agent.py
```

The ADK CLI packages your agent code, builds a container, and deploys it to Agent Engine as a Reasoning Engine resource. The resource ID looks like:
```
projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID
```

You can then query it using the Vertex AI SDK:
```python
import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="your-project", location="us-central1")
agent = reasoning_engines.ReasoningEngine("projects/.../reasoningEngines/...")
response = agent.query(input="Generate a pattern for a 3-tier web app")
```
