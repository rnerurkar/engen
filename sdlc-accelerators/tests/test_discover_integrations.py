"""discover_integrations: API Hub filter construction, response shaping, A2A>MCP>Build priority.
Live API Hub call is commented out; tests inject a fake _search."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/solution-accelerator/src"))

from clients.apigee_hub import ApigeeHubClient
from reasoning.discover_integrations import _capability_terms, discover_integrations


def test_build_filter_matches_documented_shape():
    f = ApigeeHubClient.build_filter("a2a_agent", ["body-shop-estimate"])
    assert 'attributes.type="a2a_agent"' in f
    assert 'attributes.capabilities:"body-shop-estimate"' in f
    assert 'attributes.lifecycle="active"' in f


def test_capability_terms_slugify():
    terms = _capability_terms("Body shop network — they operate their own system")
    assert "body-shop-network" in terms[0] or "body-shop" in terms[0]


def _fake():
    def search(filt):
        if "a2a_agent" in filt and "body-shop" in filt:
            return [{"name": "body-shop-agent", "display_name": "Body Shop",
                     "attributes": {"type": "a2a_agent", "capabilities": ["body-shop-estimate"],
                                    "endpoint": "https://bs/agent", "auth": "mtls",
                                    "agent_card_url": "https://bs/card.json",
                                    "lifecycle": "active", "version": "2.3.0"}}]
        if "mcp_server" in filt and "claims" in filt:
            return [{"name": "claims-db-mcp",
                     "attributes": {"type": "mcp_server", "capabilities": ["claims-lookup"],
                                    "endpoint": "mcp://claims:8443", "auth": "OAuth 2.1", "lifecycle": "active"}}]
        return []
    return ApigeeHubClient(_search=search)


def test_discovers_a2a_with_card_url_and_auth():
    r = discover_integrations(["Claims database"], ["Body shop — they operate their own"], client=_fake())
    assert len(r["a2a_agents"]) == 1
    a = r["a2a_agents"][0]
    assert a["type"] == "a2a_agent"
    assert a["capabilities"] == ["body-shop-estimate"]
    assert a["auth_method"] == "mtls"
    assert a["agent_card_url"] == "https://bs/card.json"
    assert a["version"] == "2.3.0"


def test_discovers_mcp_servers():
    r = discover_integrations(["Claims database"], [], client=_fake())
    assert any(m["name"] == "claims-db-mcp" for m in r["mcp_servers"])


def test_priority_prefer_a2a():
    r = discover_integrations(["Claims database"], ["Body shop — they operate their own"], client=_fake())
    assert r["recommendation"] == "prefer_a2a"


def test_priority_prefer_mcp_when_no_a2a():
    r = discover_integrations(["Claims database"], [], client=_fake())
    assert r["recommendation"] == "prefer_mcp"


def test_priority_build_new_when_nothing():
    r = discover_integrations(["Unknown"], [], client=ApigeeHubClient(_search=lambda f: []))
    assert r["recommendation"] == "build_new"
    assert r["a2a_agents"] == [] and r["mcp_servers"] == []


def test_dedup_same_entry_across_terms():
    # both capability terms (slug + slug-estimate) hit the same agent — must dedup
    def search(filt):
        return [{"name": "x-agent", "attributes": {"type": "a2a_agent", "capabilities": ["x"], "lifecycle": "active"}}]
    r = discover_integrations([], ["X partner — operate their own"], client=ApigeeHubClient(_search=search))
    assert len(r["a2a_agents"]) == 1   # deduped despite multiple capability terms


def test_live_call_raises_when_not_wired():
    """The live API Hub call is commented out; without _search it raises (no fabrication)."""
    import pytest
    with pytest.raises(NotImplementedError):
        ApigeeHubClient().search(api_type="a2a_agent")
