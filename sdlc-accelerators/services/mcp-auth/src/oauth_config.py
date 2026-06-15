"""OAuth 2.1 + Entra ID configuration (shared by both MCP servers).

All values are environment-specific and externalized. The single audience scope
`sdlc-accelerators.mcp` is shared by both servers — one token works for both.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class OAuthConfig:
    tenant_id: str
    client_id: str               # the IDE/Copilot public client app registration
    audience: str                # api://<app-id> or the scope audience
    required_scope: str          # sdlc-accelerators.mcp
    required_group_id: str       # Entra object ID of the "Solution Architect" AD group
    authorize_endpoint: str
    token_endpoint: str
    jwks_uri: str
    issuer: str

    @classmethod
    def from_env(cls) -> OAuthConfig:
        tenant = os.environ.get("ENTRA_TENANT_ID", "<TENANT_ID>")
        base = f"https://login.microsoftonline.com/{tenant}"
        return cls(
            tenant_id=tenant,
            client_id=os.environ.get("ENTRA_CLIENT_ID", "<CLIENT_ID>"),
            audience=os.environ.get("MCP_AUDIENCE", "api://sdlc-accelerators"),
            required_scope=os.environ.get("MCP_SCOPE", "sdlc-accelerators.mcp"),
            required_group_id=os.environ.get("SOLUTION_ARCHITECT_GROUP_ID", "<SA_GROUP_OBJECT_ID>"),
            authorize_endpoint=f"{base}/oauth2/v2.0/authorize",
            token_endpoint=f"{base}/oauth2/v2.0/token",
            jwks_uri=f"{base}/discovery/v2.0/keys",
            issuer=f"https://login.microsoftonline.com/{tenant}/v2.0",
        )
