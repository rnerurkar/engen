import subprocess
import sys
import os
import shutil

# --- Configuration ---
PROJECT_ID = "flowing-radio-459513-g8"
REGION = "us-central1"
APP_NAME = "youtube-shorts-agent"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-staging"
AGENT_DIR = "my-youtube-agent"
# Use a temp dir outside the workspace to avoid file locking/watching issues
TEMP_DIR = os.path.join(os.environ["TEMP"], "adk_deploy_custom_" + APP_NAME)

def deploy():
    print(f"🔵 Deploying '{APP_NAME}' to Vertex AI Agent Engine...")
    print(f"   Project: {PROJECT_ID}")
    print(f"   Region:  {REGION}")
    print(f"   Bucket:  {STAGING_BUCKET}")
    print(f"   Temp Dir: {TEMP_DIR}")

    # Clean up temp dir if it exists
    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up existing temp dir: {e}")

    # Construct the ADK CLI command
    # We use 'python -m google.adk.cli' to ensure we use the installed module
    command = [
        sys.executable, "-m", "google.adk.cli", "deploy", "agent_engine",
        "--project", PROJECT_ID,
        "--region", REGION,
        "--staging_bucket", STAGING_BUCKET,
        "--display_name", APP_NAME,
        "--temp_folder", TEMP_DIR,
        AGENT_DIR
    ]

    try:
        # Run the command and stream output
        # stderr=subprocess.STDOUT ensures we see all errors
        result = subprocess.run(command, check=True, text=True, stderr=subprocess.STDOUT)
        print("\n✅ Deployment command finished successfully.")
        print("   Check the output above for the 'Resource ID'.")
        print("   It will look like: projects/.../locations/.../reasoningEngines/...")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Deployment failed with exit code {e.returncode}")

if __name__ == "__main__":
    deploy()
