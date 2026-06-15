# Approved Tools — MCP Servers + A2A Agents

> The discovery surface (mirrors Apigee API Hub). Solution Accelerator queries
> API Hub via discover_integrations(); this file is the human-readable registry.
> To add a tool: register it in API Hub with type=mcp_server or type=a2a_agent.

## MCP Servers (examples)
| Name | Endpoint | Auth | Capabilities |
|---|---|---|---|
| claims-db-mcp | mcp://claims-db.company.internal:8443 | OAuth 2.1 + Workload Identity | claim_lookup, claim_create |
| policy-api-mcp | mcp://policy-api.company.internal:8443 | OAuth 2.1 + mTLS | policy_lookup, coverage_check |

## A2A Agents (examples)
| Name | Endpoint | Auth | Capabilities |
|---|---|---|---|
| body-shop-a2a | https://body-shop.partner.example/a2a | mTLS + OAuth | body-shop-estimate |

> Priority: A2A (reuse deployed agent) > MCP (existing tool) > Build (new FunctionTool).
