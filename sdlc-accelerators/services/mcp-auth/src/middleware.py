"""Auth middleware for MCP tool dispatch.

require_auth() validates the token + Solution Architect group before any tool runs.
On failure it returns the 401/403 response with a WWW-Authenticate challenge that
contains the Entra authorize endpoint — this is what makes the IDE redirect the
developer into the OAuth flow when the token is missing/invalid/expired.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

try:
    from .oauth_config import OAuthConfig
    from .token_validator import AuthError, Principal, validate_token
except ImportError:
    from oauth_config import OAuthConfig
    from token_validator import AuthError, Principal, validate_token


@dataclass
class AuthResponse:
    ok: bool
    status: int
    principal: Principal | None = None
    headers: dict | None = None
    body: dict | None = None


def authenticate(authorization_header: str | None, cfg: OAuthConfig,
                 _decode=None) -> AuthResponse:
    """Validate + authorize. Returns AuthResponse the server uses to allow or challenge."""
    try:
        principal = validate_token(authorization_header, cfg, _decode=_decode)
        return AuthResponse(ok=True, status=200, principal=principal)
    except AuthError as e:
        return AuthResponse(
            ok=False, status=e.status,
            headers={"WWW-Authenticate": e.www_authenticate(cfg)},
            body={"error": e.error, "error_description": e.description,
                  "authorization_uri": cfg.authorize_endpoint},
        )


def require_auth(cfg: OAuthConfig, _decode=None):
    """Decorator factory: gate an MCP tool handler behind auth + group membership.

    The wrapped handler receives `principal` (with sub = owner_id for tenant isolation).
    Usage:
        @require_auth(cfg)
        def blueprint_start(spec, plan, *, principal): ...
    The transport layer passes authorization_header; on failure the 401/403 + challenge
    is returned to the IDE, which restarts the Entra OAuth flow.
    """
    def decorator(handler: Callable):
        def wrapper(*args, authorization_header: str | None = None, **kwargs):
            auth = authenticate(authorization_header, cfg, _decode=_decode)
            if not auth.ok:
                return {"_auth_error": True, "status": auth.status,
                        "headers": auth.headers, "body": auth.body}
            return handler(*args, principal=auth.principal, **kwargs)
        wrapper.__name__ = getattr(handler, "__name__", "wrapped")
        return wrapper
    return decorator
