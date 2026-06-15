"""Eraser MCP client — synchronous diagram rendering via the Eraser MCP server.

The Solution Accelerator constructs the Eraser DSL and sends it to the Eraser MCP server,
which renders it synchronously and returns the .drawio.xml + .png in one call. The MCP
transport is the live seam (inject _render in tests); interface + retry + contract are real.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .base import with_retry


@dataclass
class RenderResult:
    drawio_xml: str = ""
    png_base64: str = ""


class EraserMcpClient:
    """Client for the Eraser MCP server. Synchronous render; transport is the live seam."""

    def __init__(self, endpoint: str | None = None,
                 _render: Callable[[str], dict] | None = None):
        self.endpoint = endpoint
        self._render = _render

    def render(self, dsl: str) -> RenderResult:
        """DSL -> {drawio_xml, png_base64}, synchronously, via the Eraser MCP server.
        TODO(live): MCP SDK call to the Eraser MCP server's render tool. Inject _render in tests."""
        if self._render is None:
            raise NotImplementedError(
                "Wire the Eraser MCP server transport: send the DSL to its render tool, "
                "return {drawio_xml, png_base64}. Inject _render in tests."
            )
        resp = with_retry(lambda: self._render(dsl))
        return RenderResult(drawio_xml=resp.get("drawio_xml", ""),
                            png_base64=resp.get("png_base64", ""))
