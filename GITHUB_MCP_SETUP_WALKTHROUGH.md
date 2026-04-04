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

## Setup Option 1: Local Development (Running from VS Code Terminal)

When you run agents locally — typically by opening a **VS Code terminal** and running `python -m google.adk web` or a standalone Python script — the GitHub MCP Server runs as a **child process on your workstation**. It communicates with your agent over **stdio** (standard input/output pipes): your Python process spawns the MCP server as a subprocess, and the two exchange JSON messages through the subprocess's stdin/stdout.

This is the simplest setup because everything runs on your machine. There's no cloud infrastructure involved; the only external call is from the MCP Server process to `github.com` over HTTPS.

### How It Works

```
┌────────────────────────────── VS Code ──────────────────────────────┐
│                                                                     │
│  VS Code Terminal (PowerShell)                                      │
│  > python -m google.adk web                                        │
│                                                                     │
│  ┌─────────────────────────┐                                        │
│  │  Python Process         │                                        │
│  │  (Your Agent Code)      │                                        │
│  │                         │     spawns subprocess                  │
│  │  ADK MCPToolset or      │─────────────────────┐                  │
│  │  manual MCP Client      │                     │                  │
│  │                         │   stdio (pipes)      │                  │
│  │  mcp_session.call_tool  │◄───────────────►┌───┴───────────┐     │
│  │  ("search_code", ...)   │  JSON messages  │ npx process    │     │
│  │                         │  over stdin/out │ running GitHub │     │
│  └─────────────────────────┘                 │ MCP Server     │     │
│                                              │ (Node.js)      │     │
│                                              └───────┬───────┘     │
│                                                      │             │
└──────────────────────────────────────────────────────┼─────────────┘
                                                       │ HTTPS
                                                       ▼
                                             GitHub API (github.com)
```

**What happens step by step when you start the agent from VS Code terminal:**

1. You open a PowerShell terminal in VS Code (Ctrl+`` ` ``), activate the venv, and run your agent.
2. Your Python code (via ADK's `MCPToolset` or a manual `stdio_client`) tells the OS to spawn a new process: `npx -y @modelcontextprotocol/server-github`.
3. `npx` downloads the GitHub MCP Server package (Node.js app) if not already cached, then starts it.
4. The MCP Server process's stdin and stdout are connected to your Python process via OS pipes — they exchange JSON-RPC messages through these pipes.
5. Your Python code sends an `initialize` message; the MCP Server responds with its list of available tools.
6. When the agent decides it needs to search GitHub (e.g., find a Terraform module), it calls `session.call_tool("search_code", {...})`. This sends a JSON-RPC request through the pipe to the MCP Server.
7. The MCP Server receives the request, makes an HTTPS call to `api.github.com` using the Personal Access Token you provided, and returns the result back through the pipe.
8. Your Python code receives the result and continues.

The MCP Server process stays alive for the duration of your agent's session and is automatically killed when the session ends.

### Step-by-Step Setup

#### Prerequisites

1. **Node.js** (v18 or later) — The GitHub MCP Server is a Node.js application that runs locally.
   ```powershell
   # Check if installed
   node --version
   
   # If not, install via winget (Windows) or brew (Mac)
   winget install OpenJS.NodeJS.LTS
   ```

2. **npx** — Comes bundled with Node.js. Used to download and run the MCP server without installing it globally. The first time it runs, it downloads the package; subsequent runs use the cached version.
   ```powershell
   npx --version
   ```

3. **GitHub Personal Access Token (PAT)** — The MCP server needs this to authenticate with GitHub's API.
   - Go to [github.com/settings/tokens](https://github.com/settings/tokens)
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (full control of private repos) and `read:org` (read org membership)
   - Copy the token — you'll need it in the next step

#### Configuration

Set your GitHub token as an environment variable **in the VS Code terminal** before starting the agent:

```powershell
# PowerShell (current terminal session only — disappears when you close the terminal)
$env:GITHUB_TOKEN = "ghp_your_token_here"

# Or permanently (persists across all future terminals)
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_your_token_here", "User")
```

> **Tip:** If you set the variable permanently, you need to restart VS Code (or open a new terminal) for it to take effect.

#### Option A: Using Google ADK's Built-In MCP Support (Recommended for Local Dev)

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

When you run this from VS Code terminal (`python -m google.adk web`), ADK:
1. Spawns the GitHub MCP Server as a **child process** in the background (runs `npx -y @modelcontextprotocol/server-github`)
2. Connects to it over **stdio pipes** (the same technique as piping commands in PowerShell, but with JSON messages)
3. Sends an `initialize` handshake and discovers all available tools (`search_code`, `get_file_contents`, etc.)
4. Wraps each MCP tool as a Python-callable function and adds them to the agent's tool list
5. When the agent decides it needs to search GitHub, it calls the tool — ADK serializes the request as JSON, pipes it to the MCP Server, waits for the response, and deserializes it back
6. The MCP Server process is automatically killed when `adk web` shuts down

#### Option B: Manual MCP Session (Without ADK)

If you're running a standalone Python script from the VS Code terminal (not using `adk web`), you can create the MCP session manually. This is useful for testing or debugging the GitHub MCP Client in isolation:

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

When agents are deployed to **Vertex AI Agent Engine** (formerly called Reasoning Engine), they run inside a managed container on Google Cloud. They connect to the **GitHub SaaS MCP Server** — a hosted service operated by GitHub itself, accessible over the internet via HTTPS. You do **not** need to run, deploy, or manage the MCP server yourself.

### What Is the GitHub SaaS MCP Server?

GitHub provides a **hosted, cloud-based MCP endpoint** as part of its platform. Instead of spawning a local Node.js process (like local development does), your agent connects to GitHub's server over the network using the **Streamable HTTP** transport protocol. This is the same infrastructure that powers MCP integrations in tools like GitHub Copilot, VS Code, and other MCP-enabled clients.

Key characteristics:
- **No self-hosting** — GitHub runs the server. You don't deploy anything to Cloud Run, and you don't bundle Node.js in your container.
- **Always up to date** — GitHub maintains the server with the latest tool definitions and API coverage.
- **OAuth-based authentication** — Uses a GitHub PAT (Personal Access Token) or a GitHub App for authentication, passed as a Bearer token in the HTTP request.
- **Same tools** — The SaaS server exposes the same tools as the local server (`search_code`, `get_file_contents`, `push_files`, etc.).

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
│  │     │ (HTTP mode) │      │    │
│  │     └─────┬──────┘      │    │
│  └───────────┼──────────────┘    │
│              │                   │
└──────────────┼───────────────────┘
               │ HTTPS (Streamable HTTP transport)
               ▼
      GitHub SaaS MCP Server
      (Hosted by GitHub at api.githubcopilot.com
       or github.com/mcp endpoint)
               │
               │ Internal
               ▼
         GitHub API (github.com)
```

Notice the difference from local development:
- **Local**: Your Python process spawns a Node.js subprocess on your machine, and they talk over stdin/stdout pipes.
- **Remote**: Your Python process makes HTTPS requests to GitHub's hosted MCP endpoint. No subprocess, no Node.js, no local server.

### Step-by-Step Setup

#### Step 1 — Store the GitHub Token in Secret Manager

In Agent Engine, you never hardcode secrets. Store your GitHub PAT in **Google Secret Manager**:

```bash
# Create the secret
echo -n "ghp_your_token" | gcloud secrets create github-token --data-file=-

# Grant the Agent Engine service account access
gcloud secrets add-iam-policy-binding github-token \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

In your agent code, read the secret at startup:

```python
from google.cloud import secretmanager

def get_github_token():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/github-token/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

#### Step 2 — Connect to the GitHub SaaS MCP Server

Use the **Streamable HTTP** transport to connect to GitHub's hosted endpoint. In your agent code:

```python
from google.adk.toolsets import MCPToolset
from mcp.client.streamable_http import StreamableHttpParameters

# Point to GitHub's SaaS MCP Server
github_mcp_server = StreamableHttpParameters(
    url="https://api.githubcopilot.com/mcp",  # GitHub's hosted MCP endpoint
    headers={
        "Authorization": f"Bearer {get_github_token()}"
    }
)

# Create the toolset — ADK will connect over HTTPS and discover tools
github_tools = MCPToolset(server_params=github_mcp_server)

# Pass it to your agent
agent = LlmAgent(
    name="component_spec_agent",
    model="gemini-2.0-flash",
    tools=[github_tools],
    # ... other config
)
```

When the agent starts on Agent Engine, ADK:
1. Opens an HTTPS connection to `api.githubcopilot.com/mcp`
2. Sends an `initialize` handshake with the Bearer token
3. Discovers available tools (`search_code`, `get_file_contents`, etc.)
4. Wraps each tool as a Python-callable function
5. Tool calls are sent as HTTP POST requests; responses arrive as streamed HTTP responses
6. The connection is reused across tool calls for performance

**No Node.js. No Docker customization. No extra Cloud Run service.** Just a Python HTTP client talking to GitHub's server.

#### Step 3 — Wire It Into the Component Specification Agent

The `ComponentSpecificationAgent` receives the MCP session from ADK and passes it through:

```python
class ComponentSpecificationAgent:
    def __init__(self, mcp_session):
        self.engine = ComponentSpecification(
            project_id=Config.PROJECT_ID,
            mcp_session=mcp_session,  # Active session to GitHub SaaS MCP
            github_org_repos=_get_github_repos(),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
        )
```

With a live MCP session, the `GitHubMCPTerraformClient` uses the MCP path (Tier 1) — calling `search_code` and `get_file_contents` through the SaaS server — before falling back to AWS Service Catalog (Tier 2).

### What About the PyGithub Fallback?

The system still supports a **PyGithub fallback** for maximum compatibility. If you pass `mcp_session=None`, the `GitHubMCPTerraformClient` skips MCP entirely and uses the PyGithub REST library directly. This can serve as an emergency fallback if the GitHub SaaS MCP Server is temporarily unavailable, though for production deployments on Agent Engine, the SaaS MCP Server is the recommended approach.

---

## The Decision Matrix: Which Approach When?

| Scenario | Recommended Approach | Why |
|----------|---------------------|-----|
| **Local development** (quick testing) | Option C — PyGithub fallback | Zero MCP setup; just set `GITHUB_TOKEN` |
| **Local development** (full MCP experience) | Option A — stdio via `npx` in VS Code terminal | ADK manages the local subprocess lifecycle; no infra needed |
| **Agent Engine** (production) | GitHub SaaS MCP Server (Streamable HTTP) | No self-hosting; always up to date; GitHub manages the server |
| **Agent Engine** (emergency fallback) | PyGithub fallback (`mcp_session=None`) | Works if SaaS MCP is temporarily unavailable |

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

The `ComponentSpecificationAgent` accepts an optional `mcp_session` in its constructor, which it passes through to the `GitHubMCPTerraformClient`.

- **Local (VS Code terminal)**: ADK's `MCPToolset` with `StdioServerParameters` spawns a local Node.js subprocess, creates an MCP session, and passes it through.
- **Remote (Agent Engine)**: ADK's `MCPToolset` with `StreamableHttpParameters` connects to the GitHub SaaS MCP Server over HTTPS, creates an MCP session, and passes it through.
- **Fallback (either environment)**: Pass `mcp_session=None` to skip MCP and use PyGithub REST API directly.

---

## Deployment Cheat Sheet

### Local Development (VS Code Terminal)

```powershell
# 1. Open a terminal in VS Code (Ctrl+`)

# 2. Set your GitHub token (if not already set permanently)
$env:GITHUB_TOKEN = "ghp_your_token_here"

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Run your agent (ADK will spawn the GitHub MCP Server as a local subprocess)
python -m google.adk web

# That's it — ADK starts the MCP server via npx, connects over stdio pipes,
# and your agent can call search_code, get_file_contents, etc.
```

### Agent Engine Deployment (Uses GitHub SaaS MCP Server)

```powershell
# 1. Store the GitHub token in Secret Manager
echo -n "ghp_your_token" | gcloud secrets create github-token --data-file=-

# 2. Grant Agent Engine access to the secret
gcloud secrets add-iam-policy-binding github-token `
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"

# 3. Deploy via ADK CLI (no custom Dockerfile needed — no Node.js required)
python deploy_agent.py
```

The agent connects to GitHub's SaaS MCP Server over HTTPS at runtime — no local MCP server process, no Node.js, no Cloud Run service.

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

---

## Key Difference: Local vs. Remote — Side by Side

| Aspect | Local (VS Code Terminal) | Remote (Agent Engine) |
|--------|------------------------|-----------------------|
| **MCP Server** | Local Node.js subprocess (via `npx`) | GitHub SaaS MCP Server (hosted by GitHub) |
| **Transport** | stdio (stdin/stdout pipes) | Streamable HTTP (HTTPS) |
| **ADK Config** | `StdioServerParameters` | `StreamableHttpParameters` |
| **Node.js required?** | Yes (for `npx`) | No |
| **Network call** | MCP Server → `api.github.com` | Agent → `api.githubcopilot.com/mcp` → `api.github.com` |
| **Auth** | `GITHUB_TOKEN` env var passed to MCP Server subprocess | Bearer token in HTTP header (from Secret Manager) |
| **Who manages the MCP Server?** | You (it's a subprocess on your machine) | GitHub (SaaS — fully managed) |
