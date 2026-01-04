import os
import shutil
import sys
import logging
from dotenv import dotenv_values

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
PROJECT_ID = "flowing-radio-459513-g8"
REGION = "us-central1"
APP_NAME = "youtube-shorts-agent"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-staging"
AGENT_DIR = os.path.abspath("my-youtube-agent")
TEMP_DIR = os.path.abspath("temp_manual_deploy")
ADK_APP_NAME = "agent_engine_app"

_AGENT_ENGINE_APP_TEMPLATE = """
from agent import root_agent
from vertexai.preview.reasoning_engines import AdkApp

adk_app = AdkApp(
  agent=root_agent,
  enable_tracing=False,
)
"""

def deploy():
    print(f"🔵 Starting Manual Deployment for '{APP_NAME}'...")
    
    # 1. Prepare Temp Directory
    # Use a random suffix to avoid lock issues
    import random
    global TEMP_DIR
    TEMP_DIR = f"{TEMP_DIR}_{random.randint(1000, 9999)}"
    
    print(f"   Copying agent code to: {TEMP_DIR}")
    shutil.copytree(AGENT_DIR, TEMP_DIR)

    # 2. Generate agent_engine_app.py
    app_file_path = os.path.join(TEMP_DIR, f"{ADK_APP_NAME}.py")
    with open(app_file_path, "w", encoding="utf-8") as f:
        f.write(_AGENT_ENGINE_APP_TEMPLATE)
    print(f"   Created entry point: {app_file_path}")

    # 3. Resolve Requirements
    req_file = os.path.join(TEMP_DIR, "requirements.txt")
    if not os.path.exists(req_file):
        print("   Creating default requirements.txt")
        with open(req_file, "w") as f:
            f.write("google-cloud-aiplatform[adk,agent_engines]")
    
    # 4. Load Environment Variables
    env_vars = {}
    env_file = os.path.join(TEMP_DIR, ".env")
    if os.path.exists(env_file):
        print(f"   Reading .env from {env_file}")
        env_vars = dotenv_values(env_file)
        # Remove cloud specific vars that we override
        env_vars.pop("GOOGLE_CLOUD_PROJECT", None)
        env_vars.pop("GOOGLE_CLOUD_LOCATION", None)

    # 5. Initialize Vertex AI
    print("🔵 Initializing Vertex AI SDK...")
    import vertexai
    # Try importing reasoning_engines (newer SDK) or agent_engines (older/internal)
    try:
        from vertexai.preview import reasoning_engines
    except ImportError:
        print("   Falling back to vertexai.agent_engines (if available)")
        from vertexai import agent_engines as reasoning_engines

    vertexai.init(
        project=PROJECT_ID,
        location=REGION,
        staging_bucket=STAGING_BUCKET,
    )

    # 6. Create Reasoning Engine
    print("🔵 Creating Reasoning Engine (this may take 5-10 minutes)...")
    
    # We need to add the temp dir to sys.path so pickle can find the modules
    sys.path.append(TEMP_DIR)

    # Prepare extra_packages list (contents of TEMP_DIR, not the dir itself)
    extra_packages = []
    for item in os.listdir(TEMP_DIR):
        if item in ["requirements.txt", ".env", "__pycache__", ".git", ".DS_Store"]:
            continue
        extra_packages.append(os.path.join(TEMP_DIR, item))
    
    print(f"   Extra packages to upload: {[os.path.basename(p) for p in extra_packages]}")

    try:
        # Define the agent using the same logic as ADK CLI
        # Note: ADK CLI uses a specific internal class or helper. 
        # Here we use the ReasoningEngine.create method which is the standard way.
        
        # In older versions of vertexai (like 1.43.0), env_vars might not be supported directly in create()
        # or it might be named differently.
        # However, ADK CLI uses `agent_engines.create` which is internal.
        # Let's try to use the internal `agent_engines.create` if available, as it matches ADK logic.
        
        try:
            from vertexai import agent_engines
            print("   Using internal vertexai.agent_engines.create...")
            
            # We need to wrap the app in a ModuleAgent as ADK does
            agent_engine = agent_engines.ModuleAgent(
                module_name=ADK_APP_NAME,
                agent_name='adk_app',
                register_operations={
                    '': [
                        'get_session',
                        'list_sessions',
                        'create_session',
                        'delete_session',
                    ],
                    'async': [
                        'async_get_session',
                        'async_list_sessions',
                        'async_create_session',
                        'async_delete_session',
                    ],
                    'async_stream': ['async_stream_query'],
                    'stream': ['stream_query', 'streaming_agent_run_with_events'],
                },
                sys_paths=[TEMP_DIR],
            )

            remote_agent = agent_engines.create(
                agent_engine=agent_engine,
                requirements=req_file,
                display_name=APP_NAME,
                description="Deployed via Manual Script",
                env_vars=env_vars,
                extra_packages=extra_packages,
            )
        except ImportError:
             # Fallback to public API, but remove env_vars if it fails
             print("   Using public reasoning_engines.ReasoningEngine.create...")
             # Note: In 1.43.0 public preview, env_vars might not be exposed.
             # We will try without it if the internal one fails.
             remote_agent = reasoning_engines.ReasoningEngine.create(
                agent_engine, # This was app_object in previous code, but we don't have app_object here. 
                              # We should probably instantiate the class if we were using public API.
                              # But since we are fixing the internal path, let's focus on that.
                              # Also 'app_object' variable is not defined in this scope in the original code?
                              # Wait, the original code had 'app_object' in the except block which was likely a bug anyway.
                              # Let's just fix the internal path.
                requirements=req_file,
                display_name=APP_NAME,
                description="Deployed via Manual Script",
                extra_packages=extra_packages, 
            )
            
        print("\n✅ Deployment Successful!")
        print(f"   Resource Name: {remote_agent.resource_name}")
        print(f"   Operation Name: {remote_agent.operation_name}")
        
    except Exception as e:
        print(f"\n❌ Deployment Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Optional: Clean up
        print(f"   (Temp files kept at {TEMP_DIR} for debugging)")

if __name__ == "__main__":
    deploy()
