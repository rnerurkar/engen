"""JWT validation for both MCP servers — OAuth 2.1 + Entra ID.

Validates (per architecture lines 621, 641 + your group-authz requirement):
  1. signature against Entra JWKS (cached)
  2. issuer + audience
  3. required scope (sdlc-accelerators.mcp)
  4. Solution Architect AD group membership (groups claim) — gate tool access
Extracts owner_id from the `sub` claim for Task Store tenant isolation.

On any failure raises AuthError with the right OAuth challenge so the server can
return 401 + WWW-Authenticate, which drives the IDE back through the Entra flow.
"""
from __future__ import annotations

from dataclasses import dataclass

try:
    from .oauth_config import OAuthConfig
except ImportError:
    from oauth_config import OAuthConfig


class AuthError(Exception):
    """Carries the HTTP status + WWW-Authenticate challenge for the 401/403 response."""
    def __init__(self, status: int, error: str, description: str):
        self.status = status
        self.error = error              # invalid_token | insufficient_scope | invalid_request
        self.description = description
        super().__init__(f"{error}: {description}")

    def www_authenticate(self, cfg: OAuthConfig) -> str:
        # RFC 6750 / 9728 — tells the IDE where to authenticate (drives the redirect)
        parts = [
            'Bearer realm="sdlc-accelerators"',
            f'error="{self.error}"',
            f'error_description="{self.description}"',
            f'authorization_uri="{cfg.authorize_endpoint}"',
            f'scope="{cfg.required_scope}"',
        ]
        return ", ".join(parts)


@dataclass
class Principal:
    """The authenticated, authorized developer."""
    sub: str                 # owner_id for Task Store tenant isolation
    name: str
    groups: list[str]
    scopes: list[str]


def _get_signing_key(token: str, cfg: OAuthConfig):
    """Fetch the JWKS signing key for the token's kid (cached by PyJWKClient).
    TODO(live): PyJWKClient hits cfg.jwks_uri — requires network egress to Entra."""
    import jwt
    jwks_client = jwt.PyJWKClient(cfg.jwks_uri)
    return jwks_client.get_signing_key_from_jwt(token).key


def validate_token(authorization_header: str | None, cfg: OAuthConfig,
                   _decode=None) -> Principal:
    """Validate the Bearer token and authorize the Solution Architect group.

    _decode is an injection point for tests (replaces the live jwt.decode + JWKS fetch).
    Raises AuthError (401/403) on any failure — the server turns this into the OAuth challenge.
    """
    # 1. Presence + format
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise AuthError(401, "invalid_request", "Missing or malformed Bearer token")
    token = authorization_header[len("Bearer "):].strip()
    if not token:
        raise AuthError(401, "invalid_request", "Empty Bearer token")

    # 2. Signature + standard claims (audience, issuer, exp)
    try:
        if _decode is not None:
            claims = _decode(token)
        else:  # pragma: no cover - live path needs Entra JWKS
            import jwt
            key = _get_signing_key(token, cfg)
            claims = jwt.decode(
                token, key, algorithms=["RS256"],
                audience=cfg.audience, issuer=cfg.issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
    except AuthError:
        raise
    except Exception as e:  # jwt.ExpiredSignatureError, InvalidTokenError, etc.
        raise AuthError(401, "invalid_token", f"Token validation failed: {e}") from e

    # 3. Scope
    scopes = (claims.get("scp") or "").split() if isinstance(claims.get("scp"), str) else claims.get("scp", [])
    if cfg.required_scope not in scopes:
        raise AuthError(403, "insufficient_scope",
                        f"Token missing required scope '{cfg.required_scope}'")

    # 4. Solution Architect group membership (your requirement)
    groups = claims.get("groups", []) or []
    if cfg.required_group_id not in groups:
        raise AuthError(403, "insufficient_scope",
                        "Access restricted to the Solution Architect group")

    return Principal(
        sub=claims["sub"],
        name=claims.get("name", claims.get("preferred_username", claims["sub"])),
        groups=groups,
        scopes=scopes,
    )
