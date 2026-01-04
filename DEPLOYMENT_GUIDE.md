# Agent Engine Deployment & Query Guide

This guide explains how to deploy the `my-youtube-agent` to **Vertex AI Agent Engine** and query it using Python.

## 1. Prerequisites

Ensure your environment is set up with the correct versions:

*   **Python 3.10+**
*   **Google Cloud CLI (`gcloud`)**: Installed and authenticated.
*   **Dependencies**:
    ```bash
    pip install -r my-youtube-agent/requirements.txt
    ```
    *(Ensure `google-adk==1.8.0`, `google-cloud-aiplatform==1.130.0`, `vertexai==1.43.0`)*

## 2. Deployment (Using Python)

While the ADK provides a CLI, we can wrap it in a Python script for a consistent workflow. This script packages your agent and deploys it to the Reasoning Engine.

Create a file named `deploy_agent.py` in the root of your codebase:

```python
import subprocess
import sys

# --- Configuration ---
PROJECT_ID = "flowing-radio-459513-g8"
REGION = "us-central1"
APP_NAME = "youtube-shorts-agent"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-staging"
AGENT_DIR = "my-youtube-agent"

def deploy():
    print(f"🔵 Deploying '{APP_NAME}' to Vertex AI Agent Engine...")
    print(f"   Project: {PROJECT_ID}")
    print(f"   Region:  {REGION}")
    print(f"   Bucket:  {STAGING_BUCKET}")

    # Construct the ADK CLI command
    # We use 'python -m google.adk.cli' to ensure we use the installed module
    command = [
        sys.executable, "-m", "google.adk.cli", "deploy", "agent_engine",
        "--project", PROJECT_ID,
        "--region", REGION,
        "--staging_bucket", STAGING_BUCKET,
        "--display_name", APP_NAME,
        AGENT_DIR
    ]

    try:
        # Run the command and stream output
        result = subprocess.run(command, check=True, text=True)
        print("\n✅ Deployment command finished successfully.")
        print("   Check the output above for the 'Resource ID'.")
        print("   It will look like: projects/.../locations/.../reasoningEngines/...")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Deployment failed with exit code {e.returncode}")

if __name__ == "__main__":
    deploy()
```

**To Deploy:**
```powershell
python deploy_agent.py
```

---

## 3. Querying the Deployed Agent (Using Vertex AI SDK)

Once deployed, you use the standard Vertex AI SDK to interact with your agent.

Create a file named `query_agent.py` in the root of your codebase:

```python
import vertexai
from vertexai.preview import reasoning_engines

# --- Configuration ---
PROJECT_ID = "flowing-radio-459513-g8"
REGION = "us-central1"

# ⚠️ REPLACE THIS with the Resource ID from the deployment output
REASONING_ENGINE_ID = "projects/YOUR_PROJECT_ID/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"

def query_agent():
    print(f"🔵 Connecting to Agent Engine: {REASONING_ENGINE_ID}...")
    
    # 1. Initialize SDK
    vertexai.init(project=PROJECT_ID, location=REGION)

    # 2. Load the Remote Agent
    remote_agent = reasoning_engines.ReasoningEngine(REASONING_ENGINE_ID)

    # 3. Define the Input
    # The input format depends on your agent's instruction. 
    # For the YouTube agent, a simple string prompt usually works.
    user_prompt = "Create a YouTube Short about the history of coffee."

    print(f"🤖 Sending query: '{user_prompt}'")

    # 4. Query
    try:
        response = remote_agent.query(input=user_prompt)
        print("\n✅ Agent Response:")
        print(response)
        
        # Optional: If the response is a complex object, you might inspect it:
        # print(response.get('output_key', 'No output key found'))
        
    except Exception as e:
        print(f"\n❌ Query failed: {e}")

if __name__ == "__main__":
    query_agent()
```

**To Query:**
1.  Update `REASONING_ENGINE_ID` in `query_agent.py` with your actual ID.
2.  Run:
    ```powershell
    python query_agent.py
    ```
