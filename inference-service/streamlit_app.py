import streamlit as st
import requests
import base64
import json
import time
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

def call_orchestrator(task, payload):
    """Helper to call orchestrator"""
    try:
        resp = requests.post(ORCHESTRATOR_URL, json={"task": task, "payload": payload}, timeout=600) # Increased timeout
        if resp.status_code == 200:
            return resp.json().get("result")
        else:
            st.error(f"Orchestrator Error ({resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def main():
    st.title("🏗️ EnGen: One-Shot Pattern Generator")
    
    # Session State Initialization
    if "step" not in st.session_state: st.session_state.step = "INPUT"
    if "doc_data" not in st.session_state: st.session_state.doc_data = None
    if "code_data" not in st.session_state: st.session_state.code_data = None
    
    # Progress Bar
    steps = ["Upload", "Generate Docs", "Approve Docs", "Generate Code", "Approve Code", "Publishing"]
    step_idx = 0
    if st.session_state.step == "DOC_REVIEW": step_idx = 2
    elif st.session_state.step == "CODE_GEN": step_idx = 3
    elif st.session_state.step == "CODE_REVIEW": step_idx = 4
    elif st.session_state.step == "PUBLISH": step_idx = 5
    st.progress(step_idx / 5)
    st.caption(f"Current Step: {st.session_state.step}")

    # Sidebar
    with st.sidebar:
        st.header("Process Controls")
        if st.button("Reset Workflow"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # --- Step 1: Input ---
    if st.session_state.step == "INPUT":
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Pattern Name", placeholder="e.g. Rate Limiting Service")
            uploaded_file = st.file_uploader("Upload Diagram", type=["png", "jpg", "jpeg"])
            if uploaded_file: st.image(uploaded_file, width=300)
            
        with col2:
            st.info("Ready to begin analysis.")
            if st.button("Start Analysis & Doc Gen", type="primary", disabled=not (title and uploaded_file)):
                with st.spinner("Analyzing diagram and generating documentation..."):
                    img_str = encode_image(uploaded_file)
                    res = call_orchestrator("phase1_generate_docs", {"title": title, "image_base64": img_str})
                    if res:
                        st.session_state.doc_data = res
                        st.session_state.doc_data["title"] = title # Ensure title is preserved
                        st.session_state.step = "DOC_REVIEW"
                        st.rerun()

    # --- Step 2: Doc Review ---
    elif st.session_state.step == "DOC_REVIEW":
        st.subheader("📝 Review Documentation")
        data = st.session_state.doc_data
        
        # Display Docs
        with st.expander("Show Generated Documentation", expanded=True):
            st.markdown(data.get("full_doc", ""))
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve & Publish to SharePoint"):
                with st.spinner("Publishing Docs..."):
                    # Fire and forget doc publishing
                    call_orchestrator("approve_docs", {
                        "review_id": data["review_id"], 
                        "title": data["title"],
                        "sections": data["sections"],
                        "donor_context": data["donor_context"]
                    })
                # Move immediately to next phase
                st.session_state.step = "CODE_GEN"
                st.rerun()
        with col2:
            st.warning("Editing function not implemented in this demo.")

    # --- Step 3: Code Gen (Auto-trigger) ---
    elif st.session_state.step == "CODE_GEN":
        st.info("Generating Implementation Artifacts (Terraform + Code)...")
        with st.spinner("This may take a minute..."):
            data = st.session_state.doc_data
            res = call_orchestrator("phase2_generate_code", {"full_doc": data["full_doc"]})
            if res:
                st.session_state.code_data = res
                st.session_state.step = "CODE_REVIEW"
                st.rerun()

    # --- Step 4: Code Review ---
    elif st.session_state.step == "CODE_REVIEW":
        st.subheader("💻 Review Artifacts")
        data = st.session_state.code_data
        artifacts = data.get("artifacts", {})
        
        st.json(artifacts)
        
        if st.button("Approve & Publish to GitHub"):
             with st.spinner("Publishing Code..."):
                 call_orchestrator("approve_code", {
                     "review_id": data["review_id"],
                     "artifacts": artifacts,
                     "title": st.session_state.doc_data["title"]
                 })
             st.session_state.step = "PUBLISH"
             st.rerun()

    # --- Step 5: Publishing Status ---
    elif st.session_state.step == "PUBLISH":
        st.subheader("🚀 Publishing Status")
        
        status_placeholder = st.empty()
        
        # Polling Loop
        for _ in range(60): # Poll for 60 seconds or until user leaves
            rids = [st.session_state.doc_data["review_id"], st.session_state.code_data["review_id"]]
            status_map = call_orchestrator("get_publish_status", {"review_ids": rids})
            
            with status_placeholder.container():
                # Doc Status
                doc_stat = status_map.get(rids[0], {})
                st.markdown(f"**SharePoint Docs**: `{doc_stat.get('doc_status', 'UNKNOWN')}`")
                if doc_stat.get('doc_url'): st.success(f"[Open in SharePoint]({doc_stat['doc_url']})")
                
                # Code Status
                code_stat = status_map.get(rids[1], {})
                st.markdown(f"**GitHub Code**: `{code_stat.get('code_status', 'UNKNOWN')}`")
                if code_stat.get('code_url'): st.success(f"[Open in GitHub]({code_stat['code_url']})")

            time.sleep(3)
