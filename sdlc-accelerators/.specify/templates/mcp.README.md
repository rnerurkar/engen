# Rally MCP registration — `mcp.json` (for `/accelerator.ingest-epic`)

`mcp.json` registers the **Rally MCP server** for the optional Greenfield Epic front door. Copy it to
`.vscode/mcp.json` and set the `url` for your environment.

- **Auth.** Entra ID SSO is resolved inside VS Code by the company auth extension; Rally credentials
  never leave the IDE and never reach the Solution Accelerator server.
- **Scope.** The coding agent uses the Rally MCP server's read tools (environment-specific — commonly
  `get_epic`, `query_epics`, `get_acceptance_criteria`; verify against your deployed Rally MCP server)
  to fetch the Epic **content**, then calls `ingest_epic_start` with that content only.

See Architecture Appendix § G2 and Operations Runbook § 9a. The JSON itself is kept to the keys VS Code's
`mcp.json` schema expects (`servers`, `inputs`) so strict parsers accept it.
