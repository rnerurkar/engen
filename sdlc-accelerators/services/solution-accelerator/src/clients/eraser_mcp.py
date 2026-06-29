"""Eraser MCP client — synchronous diagram rendering via the Eraser MCP server.

The Solution Accelerator constructs the Eraser DSL and sends it to the Eraser MCP server,
which renders it synchronously and returns the .drawio.xml + .png in one call. The MCP
transport is the live seam (inject _render in tests); interface + retry + contract are real.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .base import with_retry


@dataclass
class RenderResult:
    drawio_xml: str = ""
    png_base64: str = ""


class EraserMcpClient:
    """Client for the Eraser MCP server. Synchronous render; transport is the live seam."""

    def __init__(
        self,
        endpoint: str | None = None,
        _render: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self._render = _render

    def render(self, dsl: str) -> RenderResult:
        """DSL -> {drawio_xml, png_base64}, synchronously, via the Eraser MCP server.
        Inject _render in tests; otherwise runs the live MCP call (commented out below)."""
        if self._render is not None:
            resp = with_retry(lambda: self._render(dsl))  # type: ignore[misc]  # guarded non-None; mypy can't narrow self.attr into a closure
        else:
            resp = self._live_render(dsl)
        return RenderResult(
            drawio_xml=resp.get("drawio_xml", ""), png_base64=resp.get("png_base64", "")
        )

    def _live_render(self, dsl: str) -> dict[str, Any]:
        """The actual Eraser MCP server render call. COMMENTED OUT until wired.

        TO WIRE (checklist):
          1. `pip install mcp` (the MCP client SDK) — or your chosen MCP transport library.
          2. Supply self.endpoint (the Eraser MCP server URL) via EraserMcpClient(endpoint=...).
          3. Auth: attach the same OAuth 2.1 bearer token the platform uses (Entra ID) if the
             Eraser MCP server requires it; otherwise the server's own credential.
          4. Ensure network egress to the Eraser MCP server endpoint.
          5. Uncomment the body and wrap the call_tool invocation in with_retry(...).
        """
        # import asyncio
        # from mcp import ClientSession
        # from mcp.client.streamable_http import streamablehttp_client
        #
        # async def _call() -> dict:
        #     async with streamablehttp_client(self.endpoint) as (read, write, _):
        #         async with ClientSession(read, write) as session:
        #             await session.initialize()
        #             result = await session.call_tool("render", {"dsl": dsl})
        #             # The Eraser MCP server returns the rendered artifacts as structured content.
        #             content = result.structuredContent or {}
        #             return {"drawio_xml": content.get("drawio_xml", ""),
        #                     "png_base64": content.get("png_base64", "")}
        #
        # return with_retry(lambda: asyncio.run(_call()))
        raise NotImplementedError(
            "Eraser MCP render is written but commented out in _live_render. "
            "Uncomment it (+ MCP client SDK + endpoint + auth), or inject _render in tests."
        )
