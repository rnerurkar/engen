"""Apigee API Hub client — the single discovery surface for MCP servers, A2A agents, REST APIs.

INTERFACE + query construction + response shaping are real and tested. The live network call
to Apigee API Hub is written below but COMMENTED OUT (uncomment + supply credentials/SDK to wire).
A `_search` seam lets tests inject a deterministic API Hub response.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .base import with_retry


@dataclass
class ApiHubEntry:
    """One registered integration from API Hub (raw shape, before A2A/MCP/REST classification)."""
    api_id: str
    api_type: str                 # a2a_agent | mcp_server | rest_api
    display_name: str
    endpoint: str = ""
    auth_method: str = ""
    capabilities: list = field(default_factory=list)
    agent_card_url: str = ""
    lifecycle: str = "active"
    version: str = ""


class ApigeeHubClient:
    def __init__(self, project_id: str | None = None, location: str = "us-central1",
                 api_hub_instance: str | None = None,
                 _search: Callable[[str], list] | None = None):
        self.project_id = project_id
        self.location = location
        self.api_hub_instance = api_hub_instance
        self._search = _search   # test injection seam

    @staticmethod
    def build_filter(api_type: str | None = None, capabilities: list[str] | None = None,
                     lifecycle: str = "active") -> str:
        """Build an API Hub list filter. e.g. type=a2a_agent, capabilities CONTAINS 'body-shop-estimate'.
        This is the deterministic query-construction the doc describes (line 120)."""
        clauses = []
        if api_type:
            clauses.append(f"attributes.type=\"{api_type}\"")
        for cap in capabilities or []:
            clauses.append(f"attributes.capabilities:\"{cap}\"")
        if lifecycle:
            clauses.append(f"attributes.lifecycle=\"{lifecycle}\"")
        return " AND ".join(clauses)

    def search(self, api_type: str | None = None, capabilities: list[str] | None = None,
               lifecycle: str = "active") -> list[ApiHubEntry]:
        """Query API Hub and return entries. Uses the injected _search in tests; otherwise
        runs the live call (currently commented out — see _live_search)."""
        flt = self.build_filter(api_type, capabilities, lifecycle)
        if self._search is not None:
            raw = with_retry(lambda: self._search(flt))
        else:
            # Live path: the API Hub call is commented out. Raise NotImplementedError directly
            # (not through with_retry — it is not a transient failure worth retrying).
            raw = self._live_search(flt)
        return [self._to_entry(r) for r in raw]

    def _to_entry(self, r: dict) -> ApiHubEntry:
        """Shape a raw API Hub record into ApiHubEntry (tolerant of the documented attributes)."""
        attrs = r.get("attributes", r)
        return ApiHubEntry(
            api_id=r.get("name", r.get("api_id", "")),
            api_type=attrs.get("type", r.get("api_type", "")),
            display_name=r.get("display_name", r.get("displayName", r.get("name", ""))),
            endpoint=attrs.get("endpoint", r.get("endpoint", "")),
            auth_method=attrs.get("auth", attrs.get("auth_method", "")),
            capabilities=attrs.get("capabilities", []) or [],
            agent_card_url=attrs.get("agent_card_url", attrs.get("agentCardUrl", "")),
            lifecycle=attrs.get("lifecycle", "active"),
            version=str(attrs.get("version", r.get("version", ""))),
        )

    def _live_search(self, api_hub_filter: str) -> list:
        """The actual Apigee API Hub network call. COMMENTED OUT until wired.

        TO WIRE (checklist):
          1. `pip install google-cloud-apihub`
          2. Supply self.project_id + self.api_hub_instance (set via ApigeeHubClient(...) or env).
          3. Provide credentials: Application Default Credentials (ADC) — e.g.
             `gcloud auth application-default login`, or a service-account key via
             GOOGLE_APPLICATION_CREDENTIALS, with the API Hub Viewer role.
          4. Ensure network egress to apihub.googleapis.com from the runtime (Cloud Run egress
             / VPC-SC allowance as applicable).
          5. Uncomment the body below and wrap the list_apis call in with_retry(...) (it is a
             network call and should get the standard retry/backoff/timeout treatment).
        """
        # NOTE: when uncommenting, wrap the client.list_apis call in with_retry(...).
        # from google.cloud import apihub_v1
        #
        # client = apihub_v1.ApiHubClient()
        # parent = (
        #     f"projects/{self.project_id}/locations/{self.location}"
        # )
        # request = apihub_v1.ListApisRequest(parent=parent, filter=api_hub_filter)
        # results = []
        # for api in client.list_apis(request=request):
        #     # Each API may have versions/deployments carrying endpoint + auth attributes.
        #     attrs = {a.key: a.values for a in getattr(api, "attributes", [])}
        #     results.append({
        #         "name": api.name,
        #         "display_name": api.display_name,
        #         "attributes": {
        #             "type": attrs.get("type", ""),
        #             "capabilities": attrs.get("capabilities", []),
        #             "endpoint": attrs.get("endpoint", ""),
        #             "auth": attrs.get("auth", ""),
        #             "agent_card_url": attrs.get("agent_card_url", ""),
        #             "lifecycle": attrs.get("lifecycle", "active"),
        #             "version": attrs.get("version", ""),
        #         },
        #     })
        # return results
        raise NotImplementedError(
            "Apigee API Hub live call is written but commented out in _live_search. "
            "Uncomment it (+ google-cloud-apihub + credentials), or inject _search in tests."
        )
