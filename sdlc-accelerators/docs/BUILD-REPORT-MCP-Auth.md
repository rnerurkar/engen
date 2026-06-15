# Build Report — MCP Tool Exposure + OAuth 2.1 / Entra ID Auth

Closes the validation gaps: all tools exposed on both MCP servers, OAuth 2.1 + Entra ID
auth with Solution Architect group gating, IDE token flow. **59 tests passing, clean lint.**

## 1. All tools now exposed on both MCP servers

**Solution Accelerator** (`services/solution-accelerator/src/server/app.py`):
blueprint_start, blueprint_status, blueprint_result, assemble_blueprint, **validate_composition** (newly built as a named tool), refresh.

**Governance Guardian** (`services/governance-guardian/src/server/app.py` — newly built):
**assess_start, assess_status, assess_result, recordTechDebt** — the full async assess
lifecycle that was entirely missing before.

Both expose a TOOLS dict; serve() is the MCP-SDK transport-binding seam.

## 2. OAuth 2.1 + Entra ID (shared library: services/mcp-auth/)
- `oauth_config.py` — Entra endpoints, client_id, scope, audience, Solution Architect group id (all env-externalized)
- `token_validator.py` — validates JWT signature (Entra JWKS), issuer, audience, scope, AND
  Solution Architect group membership (groups claim). Extracts owner_id from sub claim.
- `middleware.py` — require_auth gate + 401/403 with WWW-Authenticate challenge (redirect)

### What's enforced (tested with REAL RS256 signed tokens)
- ✅ Valid token + Solution Architect group → authorized
- ✅ Valid token but NOT in Solution Architect group → 403 (insufficient_scope)
- ✅ Missing token → 401 + WWW-Authenticate carrying the Entra authorize_endpoint (drives IDE redirect)
- ✅ Expired token → 401 invalid_token
- ✅ Wrong/missing scope → 403
- ✅ Both servers accept the SAME token (one auth, both servers — same scope/audience/IdP)
- ✅ Tenant isolation: owner_id (sub) enforced on status/result — can't read another dev's task

## 3. The IDE ↔ Entra ↔ MCP flow (how the developer authenticates)
1. Developer runs `/accelerator.blueprint` in VSCode/Copilot.
2. IDE reads `oauth` config from preset.yml (authorize/token endpoints, client_id, scope, PKCE S256).
3. No cached token → IDE opens browser to Entra `/authorize` (PKCE) → company SSO + MFA →
   auth code → IDE exchanges at `/token` → caches access+refresh tokens in OS keychain.
4. IDE attaches `Authorization: Bearer <token>` to every MCP call.
5. MCP server validates the JWT (signature/audience/scope/group). If missing/invalid/expired →
   401/403 + WWW-Authenticate → IDE silently refreshes or restarts the browser flow.
6. Same token works on the Governance Guardian server (no re-auth).

## 4. Governance Guardian per-section assessment — Eraser MCP placeholder (per instruction)
`assessment/eraser_assess.py` — assesses each of the 8 assessable governance sections by
calling the **Eraser MCP server and its tools** to generate findings. This is a PLACEHOLDER:
the harness (iterate 8 sections, aggregate scorecard, classify showstopper/tech_debt) is real;
the Eraser MCP tool call is the injected seam. Without the Eraser MCP client, assess_start fails
cleanly with `eraser_mcp_not_wired` (no fabrication). With a stub, it produces a full scorecard.

## Seams (live wiring)
- MCP SDK transport binding on Cloud Run (serve() in both servers)
- Entra JWKS network fetch (PyJWKClient) — tests inject a decode fn
- AlloyDB-backed task store (in-memory reference today) + RLS
- The Eraser MCP client for per-section assessment

## Note on scope vs. the architecture doc
The doc specifies JWT signature + audience + sub-claim validation. The **Solution Architect
group gating** is an ADDED requirement (your instruction) implemented via the Entra `groups`
claim — a natural extension, flagged here as going beyond the documented baseline.
