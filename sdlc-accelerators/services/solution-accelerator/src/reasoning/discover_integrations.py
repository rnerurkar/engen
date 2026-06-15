"""discover_integrations — Apigee API Hub query stage (deterministic platform code).

Queries Apigee API Hub (the single discovery surface) for MCP servers, A2A agents, and REST
APIs matching the spec's data sources and external partners, and shapes the results with the
documented priority: A2A (reuse deployed agent) > MCP (use existing tool) > Build (create new).

Partners flagged "operate their own system" bias toward an A2A query (per the FNOL example:
"body shop — they operate their own" → type=a2a_agent, capabilities CONTAINS 'body-shop-estimate').

Query construction + response shaping + priority mapping are real and tested via an injected
API Hub client. The live API Hub network call lives (commented out) in ApigeeHubClient._live_search.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients.apigee_hub import ApigeeHubClient, ApiHubEntry


def _capability_terms(text: str) -> list[str]:
    """Derive candidate capability search terms from a data source / partner description.
    e.g. 'Body shop network — they operate their own system' -> ['body-shop', 'body-shop-estimate'].

    NOTE (taxonomy tuning): this slugify-and-append heuristic is a reasonable first pass that
    matches the documented FNOL example, but real capability taxonomies vary. When the live API
    Hub is wired, tune how spec descriptions map to your ACTUAL registered capability names
    (e.g. via a synonym map or an embedding match against the registered capability vocabulary).
    This is a content/taxonomy decision, not a code gap — but a slug mismatch here means a real
    registered agent/tool silently fails to be discovered, so it is worth validating against your
    actual API Hub registrations.
    """
    # take the leading noun phrase before a dash/comma, slugify
    head = re.split(r"[—\-,.:]", text, maxsplit=1)[0].strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", head).strip("-")
    terms = []
    if slug:
        terms.append(slug)
        terms.append(f"{slug}-estimate")   # common capability suffix; over-broad is fine for a filter
    return terms


def _entry_dict(e: ApiHubEntry) -> dict:
    return {
        "name": e.api_id, "display_name": e.display_name, "type": e.api_type,
        "endpoint": e.endpoint, "auth_method": e.auth_method,
        "capabilities": e.capabilities, "agent_card_url": e.agent_card_url,
        "lifecycle": e.lifecycle, "version": e.version,
    }


def discover_integrations(data_sources: list[str], partners: list[str],
                          client: ApigeeHubClient | None = None) -> dict:
    """Return discovered MCP servers, A2A agents, REST APIs from Apigee API Hub.

    client is injectable for tests (with ApigeeHubClient(_search=...)); in production it runs
    the live API Hub call. Results carry endpoint, auth, capabilities, Agent Card URL, lifecycle.
    A recommendation hint applies the A2A > MCP > Build priority.
    """
    hub = client or ApigeeHubClient()

    a2a: list[ApiHubEntry] = []
    mcp: list[ApiHubEntry] = []
    rest: list[ApiHubEntry] = []

    # Partners that operate their own system → prefer A2A discovery for their capabilities.
    for partner in partners:
        caps = _capability_terms(partner)
        a2a.extend(hub.search(api_type="a2a_agent", capabilities=caps))

    # Data sources → look for existing MCP servers and REST APIs to reuse.
    for ds in data_sources:
        caps = _capability_terms(ds)
        mcp.extend(hub.search(api_type="mcp_server", capabilities=caps))
        rest.extend(hub.search(api_type="rest_api", capabilities=caps))

    # De-duplicate by api_id (a capability term may match the same entry twice).
    def _dedup(entries):
        seen, out = set(), []
        for e in entries:
            if e.api_id and e.api_id not in seen:
                seen.add(e.api_id)
                out.append(e)
        return out

    a2a, mcp, rest = _dedup(a2a), _dedup(mcp), _dedup(rest)

    # Recommendation hint per the documented priority: A2A > MCP > Build.
    if a2a:
        recommendation = "prefer_a2a"
    elif mcp:
        recommendation = "prefer_mcp"
    else:
        recommendation = "build_new"

    return {
        "a2a_agents": [_entry_dict(e) for e in a2a],
        "mcp_servers": [_entry_dict(e) for e in mcp],
        "rest_apis": [_entry_dict(e) for e in rest],
        "recommendation": recommendation,
    }
