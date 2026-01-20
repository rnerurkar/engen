import streamlit as st
import requests
import base64
import json
import os
from config import Config

# Page Config
st.set_page_config(
    page_title="EnGen: Pattern Generator",
    page_icon="🏗️",
    layout="wide"
)

# Constants
ORCHESTRATOR_URL = f"http://localhost:{Config.ORCHESTRATOR_PORT}/invoke"

def encode_image(image_file):
    """Encode image file to base64 string"""
    return base64.b64encode(image_file.read()).decode("utf-8")

def main():
    st.title("🏗️ EnGen: One-Shot Pattern Generator")
    st.markdown("""
    Upload a software architecture diagram to generate comprehensive documentation 
    based on your organization's "Donor Patterns".
    """)

    # Sidebar for Configuration
    with st.sidebar:
        st.header("Configuration")
        st.info(f"Orchestrator URL:\n{ORCHESTRATOR_URL}")
        
    # Main Input Area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Input")
        title = st.text_input("Pattern Name / Title", placeholder="e.g. Rate Limiting Service")
        uploaded_file = st.file_uploader("Upload Architecture Diagram", type=["png", "jpg", "jpeg"])

        if uploaded_file is not None:
            st.image(uploaded_file, caption="Uploaded Diagram", use_column_width=True)

    # Action Area
    with col2:
        st.subheader("2. Generation")
        
        if uploaded_file and title:
            if st.button("Generate Documentation", type="primary"):
                with st.spinner("Running Workflow... (Analyze -> Retrieve -> Generate -> Review)"):
                    try:
                        # Prepare Payload
                        image_bg64 = encode_image(uploaded_file)
                        
                        payload = {
                            "task": "start_workflow",
                            "payload": {
                                "title": title,
                                "image_base64": image_bg64
                            }
                        }

                        # Call Orchestrator
                        response = requests.post(ORCHESTRATOR_URL, json=payload, timeout=300)
                        
                        if response.status_code == 200:
                            resp_json = response.json()
                            status = resp_json.get("status")
                            result = resp_json.get("result", {})
                            
                            if status == "completed":
                                st.success("Workflow Completed Successfully!")
                                
                                # Display Result
                                sections = result.get("sections", {})
                                if sections:
                                    for header, content in sections.items():
                                        with st.expander(header, expanded=True):
                                            st.markdown(content)
                                            
                                    # Option to download
                                    full_doc = "\n\n".join([f"# {k}\n{v}" for k,v in sections.items()])
                                    st.download_button(
                                        label="Download Markdown",
                                        data=full_doc,
                                        file_name=f"{title.lower().replace(' ', '_')}.md",
                                        mime="text/markdown"
                                    )
                                else:
                                    st.warning("Workflow finished but returned no content sections.")
                                    st.json(result)
                                    
                            else:
                                st.error(f"Workflow Failed: {resp_json.get('error')}")
                                
                        else:
                            st.error(f"HTTP Error: {response.status_code}")
                            st.text(response.text)
                            
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to Orchestrator. Is the agent running?")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
        else:
            st.info("Please provide both a Title and an Image to start.")

if __name__ == "__main__":
    main()
