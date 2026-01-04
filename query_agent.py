import vertexai
from vertexai.preview import reasoning_engines

# --- Configuration ---
PROJECT_ID = "flowing-radio-459513-g8"
REGION = "us-central1"

# ⚠️ REPLACE THIS with the Resource ID from the deployment output
# Example: "projects/123456789/locations/us-central1/reasoningEngines/987654321"
REASONING_ENGINE_ID = "projects/YOUR_PROJECT_ID/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"

def query_agent():
    print(f"🔵 Connecting to Agent Engine: {REASONING_ENGINE_ID}...")
    
    if "YOUR_ENGINE_ID" in REASONING_ENGINE_ID:
        print("❌ Error: Please update REASONING_ENGINE_ID in query_agent.py with the ID from the deployment output.")
        return

    # 1. Initialize SDK
    vertexai.init(project=PROJECT_ID, location=REGION)

    # 2. Load the Remote Agent
    try:
        remote_agent = reasoning_engines.ReasoningEngine(REASONING_ENGINE_ID)
    except Exception as e:
        print(f"❌ Failed to load Reasoning Engine: {e}")
        return

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
