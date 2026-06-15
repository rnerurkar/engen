"""apigee_hub client wrapper.
INTERFACE is real; the external call is a STUB marked TODO for live wiring.
Per root CLAUDE.md, all calls go through clients/base.with_retry.
"""
from __future__ import annotations


class ApigeeHubClient:
    def __init__(self, endpoint: str | None = None):
        self.endpoint = endpoint

    # TODO(live): replace stub bodies with real apigee_hub SDK calls.
