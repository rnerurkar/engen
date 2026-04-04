AnchorsOps.ai: Enterprise ReAct Agent (with Apigee MCP)
A Production-Ready GCP Reference Implementation

This repository contains a hardened, one-click deployable reference architecture for the ReAct (Reason + Act) Design Pattern.

The ReAct pattern allows an autonomous agent to evaluate a prompt, determine if it lacks the necessary information, seamlessly select an external tool to fetch that data, observe the result, and formulate a final response.

Marketplace Free Tier Edition: This deployment includes the complete, production-grade cloud infrastructure, pre-populated with "mock" tools (e.g., a dummy CRM lookup API) to demonstrate the architecture in action.

🏗️ Enterprise-Grade Architecture Highlights
Do not let the mock data fool you. The underlying infrastructure deployed by this repository is built to strict Google Cloud architectural standards, solving the hardest challenges of agentic AI deployments:

🛡️ Prompt Interception & LLM Security (GCP Model Armor): Direct user-to-LLM connections are an enterprise vulnerability. All inbound prompts and outbound agent responses in this architecture are automatically routed through GCP Model Armor to sanitize against prompt injections, jailbreaks, and PII/PHI data leaks before they ever hit Vertex AI.

🔌 Standardized Tool Execution (Apigee MCP Gateway): Letting an LLM directly execute API calls is a massive security risk. This architecture routes all agent tool requests through an Apigee API Gateway configured as a Model Context Protocol (MCP) Server. It enforces Spike Arrests and Quotas to prevent runaway LLM loops from DDoS-ing downstream systems, and logs all tool executions in Apigee Analytics.

🔍 Glass-Box Observability: Black-box AI is unacceptable. This deployment is fully instrumented with OpenTelemetry. You can view the exact reasoning steps, MCP tool selections, and token costs for every iteration directly within GCP Cloud Trace and Cloud Logging.

🧠 Durable Session Memory: If an underlying Cloud Run pod is terminated mid-thought, the agent does not lose its memory. All session context is persisted in real-time to GCP Firestore.

📐 Deterministic Guardrails: The ReAct agent utilizes strict structured output enforcement (Pydantic). If Vertex AI hallucinates a tool-call command, the built-in parser-retry loop catches the error and forces the LLM to self-correct, preventing pipeline failure.

🔐 Zero-Trust IAM & Secret Management: No default compute service accounts are used. The agent and the Apigee gateway utilize Workload Identity and dedicated, least-privilege GCP IAM roles. All mock API keys are dynamically retrieved from GCP Secret Manager.

⚙️ Externalized Prompt Management: Tweak the ReAct agent's behavior without triggering a CI/CD pipeline. All system prompts and persona instructions are stored externally in GCP Cloud Storage.

🚀 Quick Start (One-Click Terraform Deployment)
This entire architecture—including the Vertex AI endpoints, Model Armor policies, Apigee MCP configurations, Firestore databases, and Cloud Run services—is deployed via a single Terraform execution.

Bash
# 1. Clone the repository
git clone https://github.com/anchorsops-ai/pattern-react-mcp.git

# 2. Initialize Terraform
cd pattern-react-mcp/terraform
terraform init

# 3. Deploy to your GCP Project (Requires Owner/Editor IAM)
terraform apply -var="project_id=YOUR_PROJECT_ID"
🧪 Testing the Mock Architecture
Once deployed, the terminal will output your secure endpoint URL. You can test the ReAct agent's autonomous behavior:

User Prompt: "What is the current contract status of Acme Corp?"
Under the Hood:

Model Armor scrubs the prompt.

The Agent reasons it does not know the answer.

The Agent formats an MCP request for the get_customer_status tool.

Apigee intercepts, authenticates, and routes the MCP request to the mock Cloud Run backend.

The mock backend returns {"company": "Acme Corp", "status": "Pending Renewal"}.

The Agent observes the JSON, formulates a natural language response, and Model Armor scrubs it before returning it to the user.

🤝 Next Steps: Hydrate with Your Enterprise Data
This scaffolding is ready to be connected to your proprietary systems. Contact AnchorsOps.ai Professional Services to replace the mock CRM lookup with real-world integrations to your secure APIs, SAP ERPs, legacy databases, and enterprise data lakes using our custom MCP connectors.