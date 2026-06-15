// Component Topology
// Generated deterministically by Solution Accelerator

extract_details [icon: robot] {
  label: "extract_details"
  type: "LlmAgent"
  model: "gemini-2.0-flash"
}
fnol_coordinator [icon: workflow] {
  label: "fnol_coordinator"
  type: "SequentialAgent"
}
severity_classifier [icon: robot] {
  label: "severity_classifier"
  type: "LlmAgent"
  model: "gemini-2.0-flash"
}
body_shop_a2a [icon: building] { label: "body-shop-a2a" type: "a2a_agent" }
claims_db_mcp [icon: database] { label: "claims-db-mcp" type: "mcp_server" }
coverage_calculator_fn [icon: code] { label: "coverage_calculator_fn" type: "function_tool" }
severity_classifier_fn [icon: code] { label: "severity_classifier_fn" type: "function_tool" }
fnol_coordinator > extract_details: "delegates"
fnol_coordinator > severity_classifier: "delegates"
extract_details > claims_db_mcp: "mcp_server"
extract_details > coverage_calculator_fn: "function_tool"
severity_classifier > body_shop_a2a: "a2a_agent"
severity_classifier > severity_classifier_fn: "function_tool"
