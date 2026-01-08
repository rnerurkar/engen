Enterprise Knowledge Intelligence Framework - SharePoint Version 2.1
Design Document: Agentic RAG with Vertex AI Search & SP Connector

1. Introduction
This design defines an Agentic RAG (Retrieval Augmented Generation) architecture capable of ingesting, understanding, and answering complex queries across a corporate SharePoint ecosystem.

The core of this design leverages the Google Cloud Vertex AI Search SharePoint Connector in Data Ingestion Mode. By ingesting data into a Google-managed index (rather than using Federated Search), the system enables semantic understanding, cross-document reasoning, and multimodal analysis (text, charts, images).

The architecture is divided into two planes:

Ingestion Plane: Secure synchronization of SharePoint artifacts and ACLs; handles Master-Detail relationships where list items point to detailed pages.

Inference Plane: Runtime environment where an ADK Agent orchestrates retrieval using tools to answer user queries via Gemini 1.5 Pro.

2. Ingestion Plane Design
The Ingestion Plane moves data from the Microsoft tenant to Google Cloud while maintaining security boundaries and data fidelity.

2.1 SharePoint Data Store Setup Step-by-Step
To support Data Ingestion and Real-time Sync, perform the following configuration steps.

Prerequisites

Google Cloud Project: Active project with billing enabled.

SharePoint Online Account: Administrative access to the SharePoint instance.

Microsoft Entra Access: Permissions to register applications and grant admin consent.

Step 1 Register Application in Microsoft Entra ID
Navigate to Microsoft Entra Admin Center > App registrations > New registration.

Name: VertexAISearch-SharePointConnector.

Supported Account Types: Accounts in this organizational directory only.

Redirect URI: Web → https://vertexaisearch.cloud.google.com/console/oauth/sharepoint_oauth.html.

Record Application (client) ID and Directory (tenant) ID.

Step 2 Configure Federated Credentials Security
In the App Registration, go to Certificates & secrets > Federated credentials > Add credential.

Issuer: https://accounts.google.com.

Subject Identifier: Obtain from Google Cloud Console during Data Store creation and paste here.

Step 3 Grant API Permissions
API permissions > Add a permission > Microsoft Graph.

Add Application permissions: Sites.FullControl.All and User.Read.All (for identity syncing).

Add SharePoint Permissions: Sites.FullControl.All.

Click Grant admin consent for [Tenant Name].

Step 4 Create Data Store in Vertex AI Agent Builder
In Google Cloud Console: Agent Builder > Data Stores > Create Data Store.

Select SharePoint Online as the source.

Authentication: Enter Client ID and Tenant ID from Step 1. No client secret required if using Federated Credentials.

2.2 Processing Images Charts and Tables
Problem: The default SharePoint connector extracts plain text, which flattens tables and ignores images/charts without alt text, causing loss of structured content.

Solution: Configure the Data Store with Document AI capabilities and layout-aware parsing during initial setup. This requires recreating the store if not enabled initially.

Configuration Checklist

Chunking Strategy: Use layout-aware chunking.

Parser: Select Layout Parser backed by Document AI.

Enable Table Annotation: Preserve row/column structure and convert tables into structured formats (Markdown or HTML).

Enable Image Annotation / OCR: Extract text inside images and charts so the Agent can read labels and numbers.

Note on Cost and Latency: Enabling visual analysis increases indexing costs and ingestion latency.

Comparison of Ingestion Modes
Feature	Standard Ingestion Default	Ingestion with Layout Parser
Tables	Flattened text; structure lost.	Preserves structure (Markdown/HTML).
Charts	Ignored / Invisible.	OCR extracts title, axis labels, and data points.
Images	Ignored.	Captures text inside images (receipts, diagrams).
Headings	Plain text.	Hierarchical chunking preserves context.
2.3 Double-Sync Security Architecture
To address ACL propagation delay, use two parallel sync processes:

Content Sync: Connector uses Real-time/Incremental Sync to update files, pages, and permissions.

Identity Sync: Configure Google Cloud Directory Sync (GCDS) to run frequently (e.g., every 15–30 minutes) to sync Entra ID group memberships to Google Cloud Identity.

2.4 Ingestion Plane Diagrams
Component Diagram: Ingestion Plane

Figure placeholder: Diagram showing flow between SharePoint Online, Entra ID, Vertex AI SharePoint Connector, Document AI, GCDS, Google Cloud Identity, Vertex AI Search Data Store, and ACL Index.

Mermaid flowchart (original diagram converted to Mermaid):

mermaid
graph TD
  subgraph Azure["Microsoft Azure / SharePoint Tenant"]
    SP["SharePoint Online (Sites, Lists, Drive)"]
    Entra["Entra ID / Azure AD (Users & Groups)"]
  end

  subgraph GCP["Google Cloud Platform"]
    subgraph Identity["Identity Layer"]
      GCDS["Google Cloud Directory Sync (GCDS)"]
      CloudID["Google Cloud Identity"]
    end
  end

  subgraph Ingestion["Ingestion Pipeline"]
    Connector["Vertex AI SharePoint Connector"]
    DocAI["Document AI (Layout Parser & OCR)"]
  end

  subgraph Storage["Data Storage"]
    Index["Vertex AI Search Data Store (Vector & Metadata Index)"]
    ACL_Store["ACL Index"]
  end

  SP -->|Real-time/Incremental Sync (Files, Pages, Permissions)| Connector
  Entra -->|LDAP / API Sync| GCDS
  GCDS -->|Sync Users & Groups| CloudID

  Connector -->|Check Identity Mapping| CloudID
  Connector -->|Send Docs for Parsing| DocAI
  DocAI -->|Extract Text, Tables, Image Metadata| Connector
  Connector -->|Index Chunks + ACLs| Index
  Connector -->|Map Permissions| ACL_Store
Sequence Diagram: Ingestion Pipeline

mermaid
sequenceDiagram
  autonumber
  participant SP as SharePoint Online
  participant Entra as Azure AD (Entra)
  participant GCDS as GCDS (Sync Tool)
  participant CloudID as Google Cloud Identity
  participant Connect as Vertex AI Connector
  participant DocAI as Document AI (Layout Parser)
  participant VAI as Vertex AI Index

  Note over SP,VAI: Parallel Process: Identity Synchronization
  Entra->>GCDS: 1. Delta Sync (Group Membership Changes)
  GCDS->>CloudID: 2. Update User/Group Mappings

  Note over SP,VAI: Parallel Process: Content Ingestion
  SP->>Connect: 3. Change Event (File/Page Created or Updated)
  Connect->>Connect: 4. Fetch File Content + ACL Metadata

  rect rgb(240,248,255)
    Connect->>DocAI: 5. Send Binary (PDF/HTML/Image)
    DocAI-->>DocAI: 6. OCR Images, Parse Tables, Chunk by Header
    DocAI-->>Connect: 7. Return Structured Chunks (Text + Image Metadata)
  end

  Connect->>CloudID: 8. Resolve ACLs (Map Azure User -> Google User)
  Connect->>VAI: 9. Upsert Vector Embeddings + ACLs + Metadata
  VAI-->>Connect: 10. Acknowledge Indexing
3. Inference Plane Design
The Inference Plane uses an Agentic RAG workflow. The Agent orchestrates retrieval using a custom tool to answer user queries via Gemini 1.5 Pro.

3.1 Multimodal Agentic Workflow
Use a Retrieve, Then View pattern:

Search Tool: Returns text and metadata (including image annotations).

Visual Fetch Tool: Fetches raw image bytes when visual analysis is required.

Multimodal Model: Gemini 1.5 Pro performs reasoning on text + image.

Example flow for a multimodal query:  
User: "Look at the sales chart in the Q3 Report and tell me if it is volatile."

Retrieval: Agent uses SharePointSearchTool with query "Q3 Report sales chart". Search returns a chunk like "Figure 3: Sales Trend 2024" with metadata file_path and page_number.

Visual Acquisition: Agent calls VisualFetchTool (custom wrapper around MS Graph API) to fetch page image bytes: fetch_page_image(file_path, page=12).

Multimodal Generation: Agent calls Gemini 1.5 Pro with prompt and image bytes. Gemini analyzes jagged lines and concludes volatility.

3.2 Inference Plane Diagrams
Component Diagram: Agentic RAG Workflow

Figure placeholder: Diagram showing Client Side (Streamlit), ADK Agent Runtime, Tools (VertexAISearchTool, MSGraphFileFetcher), Vertex AI Search, MS Graph API, Gemini 1.5 Pro, and SharePoint Storage.

Mermaid flowchart (inference):

mermaid
graph TD
  subgraph Client Side
    User[End User]
    Streamlit[Streamlit Chatbot App]
  end

  subgraph ADK Agent Runtime (Python)
    Agent["ADK LLMAgent (Orchestrator)"]
    subgraph Tools
      SearchTool[VertexAISearchTool]
      FetchTool[MSGraphFileFetcher (Custom Tool)]
    end
  end

  subgraph Google Cloud Platform
    VAIS["Vertex AI Search (SharePoint Data Store)"]
    Gemini["Gemini 1.5 Pro (Multimodal Model)"]
  end

  subgraph Microsoft Graph
    GraphAPI[MS Graph API]
    SP_Store[SharePoint Storage]
  end

  User -->|Message| Streamlit
  Streamlit -->|Session State + User Email| Agent

  Agent -->|1. Query + User Info (ACL)| SearchTool
  SearchTool -->|Search Request| VAIS
  VAIS -->|Text Chunks + File Metadata| SearchTool
  SearchTool -->|Results| Agent

  Agent -->|2. If Visual Analysis Needed| FetchTool
  FetchTool -->|Get File Stream| GraphAPI
  GraphAPI -->|Read File| SP_Store
  SP_Store -->|Raw Data| GraphAPI
  GraphAPI -->|File Bytes| FetchTool
  FetchTool -->|Image Bytes| Agent

  Agent -->|3. Prompt + Context + Image Bytes| Gemini
  Gemini -->|Multimodal Response| Agent
  Agent -->|Final Answer| Streamlit
Sequence Diagram: Inference Workflow

mermaid
sequenceDiagram
  autonumber
  actor User
  participant Streamlit
  participant Agent as ADK Agent (LLMAgent)
  participant Search as Vertex AI Search Tool
  participant Fetch as MS Graph Fetch Tool
  participant Gemini as Gemini 1.5 Pro

  User->>Streamlit: "Look at the sales chart in the Q3 Report. Is it volatile?"
  Streamlit->>Agent: Send Prompt + User Email (alice@example.com)

  rect rgb(230,240,255)
    Note right of Agent: Phase 1: Discovery (Text/Metadata)
    Agent->>Search: search("Q3 Report sales chart", user="alice@example.com")
    Search-->>Agent: Result: Found "Q3_Report.pdf", Page 12 (Title: Sales Trends)
  end

  rect rgb(255,240,245)
    Note right of Agent: Phase 2: Visual Acquisition
    Agent->>Fetch: get_page_image(file_id="...", page=12)
    Fetch->>Fetch: Download PDF via Graph API -> Convert P.12 to JPG
    Fetch-->>Agent: Returns: <Image_Bytes>
  end

  rect rgb(240,255,240)
    Note right of Agent: Phase 3: Multimodal Generation
    Agent->>Gemini: Generate(Prompt + Text Context + <Image_Bytes>)
    Gemini-->>Agent: "The chart on Page 12 shows high volatility with sharp spikes..."
  end

  Agent->>Streamlit: Final Response
4. Agentic RAG Implementation Production Code and Logic
This section provides production-ready implementation details for three use cases: Master-Detail synthesis, Table extraction, and Multimodal chart analysis.

4.1 Use Case 1 Master-Detail List-Detail Relationship
Goal: Answer queries requiring information from both a SharePoint List Item (e.g., Pattern Catalog) and the linked detailed page.

Agentic Join Pattern: The SharePoint Connector indexes Lists and Pages separately; the Agent must bridge them.

Implementation (Python)

python
from google.cloud import discoveryengine_v1 as discoveryengine

class MasterDetailTool(Tool):
    # Orchestrates retrieval of a List Item and its linked Detail Page.

    def run(self, pattern_name: str, user_email: str):
        # Step 1: Search for the Master List Item
        user_info = discoveryengine.UserInfo(user_id=user_email)

        list_request = discoveryengine.SearchRequest(
            query=f"{pattern_name} AND context:\"Pattern Catalog\"",
            user_info=user_info,
            page_size=1
        )
        list_response = self.client.search(request=list_request)

        if not list_response.results:
            return "Pattern not found in Catalog."

        # Extract Metadata
        item = list_response.results[0].document.derived_struct_data
        status = item.get('Status', 'Unknown')
        owner = item.get('Owner', 'Unknown')

        # KEY STEP: Extract the Link to the Detail Page
        detail_url = item.get('LinkToDocumentation', None)

        if not detail_url:
            return f"Found Pattern: {pattern_name} (Status: {status}), but no detail link exists."

        # Step 2: Search for the Detail Page Content using the URL as a filter
        detail_request = discoveryengine.SearchRequest(
            query=pattern_name,
            filter=f'url: "{detail_url}"',
            user_info=user_info
        )
        detail_response = self.client.search(request=detail_request)

        # Step 3: Synthesize
        detail_content = detail_response.results[0].document.derived_struct_data.get('snippets')[0]['snippet']

        return f"""
** Pattern Metadata (from List) :**
- Name: {pattern_name}
- Status: {status}
- Owner: {owner}

** Detail Documentation (from Page) :**
{detail_content}
"""
4.2 Use Case 2 SP Detail Page Query about Tables
Goal: Accurately answer questions about specific rows/columns in a table (e.g., "What is the SLA for Silver Tier?").

Logic: With Layout Parser and Table Annotation enabled, tables are indexed as structured Markdown/HTML. The standard search tool returns structured chunks; set max_extractive_answer_count to 1 for precise table row hits.

Search Request Example

python
request = discoveryengine.SearchRequest(
    content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_answer_count=1
        )
    ),
    # ... other params ...
)
LLM Prompt Strategy for Tables

If the search result contains a Markdown table (e.g., | Col A | Col B |), read the row corresponding to the user's query and return the requested column value.

4.3 Use Case 3 SP Detail Page Query about Charts and Images
Goal: Provide visual analysis of a chart (e.g., "Is the trend increasing?").

A The MSGraphFetcher Implementation
This class fetches files from SharePoint via MS Graph and converts specific pages to images.

python
import os
import requests
import msal
import base64
from io import BytesIO
from pdf2image import convert_from_bytes
from typing import Optional, Any

class MSGraphFetcher:
    # Production tool to fetch files from SharePoint via MS Graph and convert pages to images.

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = ["https://graph.microsoft.com/.default"]

        # Initialize MSAL Confidential Client
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )

    def _get_headers(self) -> dict:
        """Helper to get a valid access token."""
        result = self.app.acquire_token_silent(self.scopes, account=None)
        if not result:
            result = self.app.acquire_token_for_client(scopes=self.scopes)
        if "access_token" in result:
            return {"Authorization": f"Bearer {result['access_token']}"}
        else:
            raise Exception(f"Could not acquire token: {result.get('error_description')}")

    def _resolve_sharepoint_url_to_drive_item(self, sharepoint_url: str) -> str:
        # Convert URL to Graph driveItem ID using /shares endpoint encoding.
        b64_url = base64.urlsafe_b64encode(sharepoint_url.encode("utf-8")).decode("utf-8")
        encoded_url = "u!" + b64_url.rstrip("=")
        endpoint = f"{self.base_url}/shares/{encoded_url}/driveItem"
        response = requests.get(endpoint, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()["id"]
        else:
            raise Exception(f"Failed to resolve URL: {sharepoint_url}. Graph Error: {response.text}")

    def get_page_image(self, file_url: str, page_number: int) -> bytes:
        # Downloads the PDF and converts the specific page to JPEG bytes.
        try:
            # Resolve URL to Graph ID
            drive_item_id = self._resolve_sharepoint_url_to_drive_item(file_url)

            # Construct download URL using /shares resolution
            download_url = f"{self.base_url}/shares/u!{base64.urlsafe_b64encode(file_url.encode('utf-8')).decode('utf-8').rstrip('=')}/driveItem/content"
            response = requests.get(download_url, headers=self._get_headers(), stream=True)
            if response.status_code != 200:
                raise Exception(f"Failed to download file content: {response.text}")

            pdf_bytes = response.content

            # Convert specific page to image
            images = convert_from_bytes(
                pdf_bytes,
                first_page=page_number,
                last_page=page_number,
                fmt="jpeg"
            )
            if not images:
                raise Exception(f"Page {page_number} could not be extracted (File might be too short).")

            img_byte_arr = BytesIO()
            images[0].save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()

        except Exception as e:
            print(f"Error in MSGraphFetcher: {str(e)}")
            return None
B The MultimodalChartAgent Implementation
This class orchestrates search and visual fetch, then sends text + image to Gemini 1.5 Pro.

python
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from google.cloud import discoveryengine_v1 as discoveryengine

class MultimodalChartAgent:
    def __init__(self, project_id, location, data_store_id, graph_creds: dict):
        self.project_id = project_id

        # Initialize Gemini 1.5 Pro (Multimodal)
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-1.5-pro-001")

        # Initialize Search Client
        self.search_client = discoveryengine.SearchServiceClient()
        self.serving_config = self.search_client.serving_config_path(
            project=project_id,
            location=location,
            data_store=data_store_id,
            serving_config="default_search"
        )

        # Initialize Graph Fetcher
        self.graph_fetcher = MSGraphFetcher(
            tenant_id=graph_creds['tenant_id'],
            client_id=graph_creds['client_id'],
            client_secret=graph_creds['client_secret']
        )

    def find_document_location(self, query: str, user_email: str):
        # Helper: Searches Vertex AI to find the File URL and Page Number.
        user_info = discoveryengine.UserInfo(user_id=user_email)
        request = discoveryengine.SearchRequest(
            serving_config=self.serving_config,
            query=query,
            page_size=3,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                ),
                extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                    max_extractive_answer_count=1
                )
            ),
            user_info=user_info
        )
        response = self.search_client.search(request=request)

        if not response.results:
            return None, None, "No results found."

        best_doc = response.results[0].document.derived_struct_data
        file_url = best_doc.get('link', None)

        # Extract page number if available
        page_num = 1
        if hasattr(response.results[0], 'pages'):
            page_num = int(response.results[0].pages[0])
        elif 'page_number' in best_doc:
            page_num = int(best_doc['page_number'])

        return file_url, page_num, best_doc.get('title')

    def run(self, user_query: str, user_email: str):
        print(f"--- Agent Received Query: {user_query} ---")

        # Step 1: Discovery
        file_url, page_num, title = self.find_document_location(user_query, user_email)
        if not file_url:
            return "I couldn't find any documents matching your request."

        print(f"Step 1: Found Document '{title}' at URL: {file_url} (Page {page_num})")

        # Step 2: Visual Fetch
        print("Step 2: Fetching visual context via MS Graph...")
        image_bytes = self.graph_fetcher.get_page_image(file_url, page_num)
        if not image_bytes:
            return f"I found the document '{title}', but I couldn't retrieve the visual page image due to permissions or format issues."

        # Step 3: Multimodal Reasoning
        print("Step 3: Sending Text + Image to Gemini 1.5 Pro...")
        prompt = f"""
You are an expert analyst.
The user asked: "{user_query}"

Attached is an image of Page {page_num} from the document "{title}".
Analyze the charts, diagrams, or tables in this image to answer the user's question.
Be specific about data points you see.
"""
        response = self.model.generate_content([
            Part.from_text(prompt),
            Part.from_data(data=image_bytes, mime_type="image/jpeg")
        ])

        return response.text
C Example Usage in Production
python
if __name__ == "__main__":
    # Configuration (Load from Env Variables in prod)
    PROJECT_ID = "my-gcp-project"
    LOCATION = "global"
    DATA_STORE_ID = "sharepoint-ds-id"

    GRAPH_CREDS = {
        "tenant_id": "my-azure-tenant-id",
        "client_id": "my-azure-client-id",
        "client_secret": "my-azure-client-secret"
    }

    # Instantiate
    agent = MultimodalChartAgent(PROJECT_ID, LOCATION, DATA_STORE_ID, GRAPH_CREDS)

    # Run Query
    answer = agent.run(
        user_query="Look at the 'Quarterly Revenue' chart in the Q3 Financial Report. Is the growth consistent?",
        user_email="alice@company.com"
    )
    print("\n--- Final Answer ---")
    print(answer)
5. Conclusion Vertex AI Search vs Custom Pipeline
Summary placeholder: The document compares Vertex AI Search (with Document AI and layout-aware ingestion) against building a fully custom pipeline. Key trade-offs include indexing fidelity, multimodal capabilities, cost, latency, and operational complexity.

Appendix Placeholders and Notes
Figures: All figures in the original document are represented as placeholders above. Replace placeholders with actual images or diagrams as needed.

Tables: Tables were converted to Markdown where present.

Code Blocks: Python and Mermaid code blocks are preserved and formatted for readability.

Security Notes: Ensure federated credentials, API permissions, and admin consent are configured correctly before production use.

Operational Notes: Enabling Document AI features increases cost and ingestion latency; plan capacity and sync cadence accordingly.