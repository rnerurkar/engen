"""
HA/DR Diagram Generator
-----------------------
Generates SVG component diagrams and draw.io XML files for every combination
of DR Strategy × Lifecycle Phase (4 × 3 = 12 diagrams per pattern).

Each diagram shows the services in the pattern and their state (Active,
Standby, Scaled-Down, Not-Deployed, etc.) under a specific DR strategy and
lifecycle phase.

Artefacts produced per diagram:
  - SVG  (embedable in HTML / SharePoint pages)
  - PNG  (fallback image via cairosvg)
  - draw.io XML  (stored on GCS so architects can edit in draw.io)

Provides both sync (``generate_all_diagrams``) and async
(``agenerate_all_diagrams``) entry-points.  The async variant
parallelises all 12 diagram generations via ``asyncio.gather``.
"""

import asyncio
import io
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class DiagramArtifact:
    """A single diagram (one DR strategy + one lifecycle phase)."""
    dr_strategy: str
    lifecycle_phase: str
    svg_content: str = ""
    drawio_xml: str = ""
    png_bytes: bytes = b""
    description: str = ""
    is_fallback: bool = False


@dataclass
class PatternDiagramBundle:
    """All diagrams for every DR-strategy × lifecycle-phase combination."""
    pattern_name: str
    diagrams: Dict[Tuple[str, str], DiagramArtifact] = field(default_factory=dict)

    def get(self, strategy: str, phase: str) -> Optional[DiagramArtifact]:
        return self.diagrams.get((strategy, phase))

    def all_artifacts(self) -> List[DiagramArtifact]:
        return list(self.diagrams.values())


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

DR_STRATEGIES = [
    "Backup and Restore",
    "Pilot Light On Demand",
    "Pilot Light Cold Standby",
    "Warm Standby",
]

LIFECYCLE_PHASES = [
    "Initial Provisioning",
    "Failover",
    "Failback",
]

# Colour palette for service states (used in prompt examples)
STATE_COLORS = {
    "Active":       "#4CAF50",  # green
    "Standby":      "#FF9800",  # amber
    "Scaled-Down":  "#03A9F4",  # light-blue
    "Not-Deployed": "#9E9E9E",  # grey
    "Restoring":    "#E91E63",  # pink
    "Syncing":      "#9C27B0",  # purple
}

# One-shot SVG example for the LLM prompt
SVG_ONE_SHOT_EXAMPLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
    </marker>
  </defs>
  <style>
    text { font-family: Arial, sans-serif; font-size: 13px; }
    .title { font-size: 18px; font-weight: bold; }
    .region-label { font-size: 15px; font-weight: bold; fill: #333; }
    .svc-label { font-size: 12px; fill: #fff; }
    .state-label { font-size: 11px; font-style: italic; }
  </style>
  <!-- Title -->
  <text x="400" y="30" text-anchor="middle" class="title">Backup and Restore — Initial Provisioning</text>
  <!-- Primary Region -->
  <rect x="30" y="50" width="350" height="400" rx="12" fill="#E3F2FD" stroke="#1565C0" stroke-width="2"/>
  <text x="205" y="80" text-anchor="middle" class="region-label">Primary Region</text>
  <!-- Service box -->
  <rect x="60" y="100" width="140" height="50" rx="8" fill="#4CAF50"/>
  <text x="130" y="130" text-anchor="middle" class="svc-label">Amazon RDS</text>
  <text x="130" y="160" text-anchor="middle" class="state-label" fill="#388E3C">Active</text>
  <!-- DR Region -->
  <rect x="420" y="50" width="350" height="400" rx="12" fill="#FFF3E0" stroke="#E65100" stroke-width="2"/>
  <text x="595" y="80" text-anchor="middle" class="region-label">DR Region</text>
  <rect x="450" y="100" width="140" height="50" rx="8" fill="#9E9E9E"/>
  <text x="520" y="130" text-anchor="middle" class="svc-label">Amazon RDS</text>
  <text x="520" y="160" text-anchor="middle" class="state-label" fill="#616161">Not-Deployed</text>
  <!-- Arrow -->
  <line x1="200" y1="125" x2="445" y2="125" stroke="#333" stroke-width="1.5" marker-end="url(#arrowhead)"/>
</svg>"""

# One-shot draw.io XML example
DRAWIO_ONE_SHOT_EXAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io">
  <diagram name="Backup and Restore - Initial Provisioning" id="diag1">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- Primary Region container -->
        <mxCell id="2" value="Primary Region" style="rounded=1;whiteSpace=wrap;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="30" y="50" width="350" height="400" as="geometry"/>
        </mxCell>
        <!-- Service: Amazon RDS (Active) -->
        <mxCell id="3" value="Amazon RDS&#xa;[Active]" style="rounded=1;whiteSpace=wrap;fillColor=#4CAF50;fontColor=#ffffff;strokeColor=#388E3C;" vertex="1" parent="1">
          <mxGeometry x="60" y="100" width="140" height="50" as="geometry"/>
        </mxCell>
        <!-- DR Region container -->
        <mxCell id="4" value="DR Region" style="rounded=1;whiteSpace=wrap;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="420" y="50" width="350" height="400" as="geometry"/>
        </mxCell>
        <!-- Service: Amazon RDS (Not-Deployed) -->
        <mxCell id="5" value="Amazon RDS&#xa;[Not-Deployed]" style="rounded=1;whiteSpace=wrap;fillColor=#9E9E9E;fontColor=#ffffff;strokeColor=#757575;" vertex="1" parent="1">
          <mxGeometry x="450" y="100" width="140" height="50" as="geometry"/>
        </mxCell>
        <!-- Arrow -->
        <mxCell id="6" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="3" target="5" parent="1">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""


# ──────────────────────────────────────────────────────────────────────────────
# Generator class
# ──────────────────────────────────────────────────────────────────────────────

class HADRDiagramGenerator:
    """
    Generates component-level SVG diagrams and draw.io XML files for every
    combination of DR strategy and lifecycle phase using Gemini.
    """

    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self._init_model()

    def _init_model(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction=(
                    "You are a Principal Cloud Architect and technical "
                    "illustrator. You generate accurate, clean SVG component "
                    "diagrams and draw.io XML files for enterprise HA/DR "
                    "architectures."
                ),
            )
            logger.info("HADRDiagramGenerator model initialised")
        except Exception as e:
            logger.error(f"Failed to initialise diagram model: {e}")
            self.model = None

    # ─── Public API ──────────────────────────────────────────────────────

    def generate_all_diagrams(
        self,
        pattern_name: str,
        services: List[str],
        hadr_text_sections: Dict[str, str],
        pattern_context: Dict[str, Any],
    ) -> PatternDiagramBundle:
        """
        Generate diagrams for every DR-strategy × lifecycle-phase combination.

        Args:
            pattern_name:       Human-readable pattern title.
            services:           List of canonical service names in the pattern.
            hadr_text_sections: Output of HADRDocumentationGenerator — maps
                                DR strategy → generated Markdown text.
            pattern_context:    Pattern metadata (title, solution overview, etc.)

        Returns:
            PatternDiagramBundle with up to 12 DiagramArtifact entries.
        """
        bundle = PatternDiagramBundle(pattern_name=pattern_name)

        for strategy in DR_STRATEGIES:
            strategy_text = hadr_text_sections.get(strategy, "")
            # Split the strategy text into per-phase sections
            phase_texts = self._split_phases(strategy_text)

            for phase in LIFECYCLE_PHASES:
                phase_text = phase_texts.get(phase, "")
                logger.info(
                    f"Generating diagram: {strategy} / {phase}"
                )

                artifact = self._generate_single_diagram(
                    pattern_name=pattern_name,
                    services=services,
                    dr_strategy=strategy,
                    lifecycle_phase=phase,
                    phase_description=phase_text,
                    pattern_context=pattern_context,
                )
                bundle.diagrams[(strategy, phase)] = artifact

        total = len(bundle.diagrams)
        fallbacks = sum(1 for a in bundle.all_artifacts() if a.is_fallback)
        logger.info(
            f"Generated {total} diagrams for '{pattern_name}' "
            f"({fallbacks} fallbacks)"
        )
        return bundle

    # ─── Async public API ────────────────────────────────────────────────

    async def agenerate_all_diagrams(
        self,
        pattern_name: str,
        services: List[str],
        hadr_text_sections: Dict[str, str],
        pattern_context: Dict[str, Any],
        timeout_per_diagram: float = 180.0,
        max_concurrent: int = 4,
    ) -> PatternDiagramBundle:
        """
        Async version of ``generate_all_diagrams`` — generates up to 12
        diagrams in parallel using ``asyncio.gather``.

        Each diagram involves two Gemini calls (SVG + draw.io) and a local
        SVG→PNG conversion.  All three are CPU/IO-bound and offloaded to
        threads so the event loop stays free.

        Args:
            pattern_name:         Human-readable pattern title.
            services:             List of canonical service names.
            hadr_text_sections:   DR strategy → generated Markdown text.
            pattern_context:      Pattern metadata.
            timeout_per_diagram:  Max seconds per single diagram
                                  (SVG + draw.io + PNG combined, default 180).
            max_concurrent:       Concurrency cap to avoid Gemini quota
                                  exhaustion (default 4 at a time).

        Returns:
            PatternDiagramBundle with up to 12 DiagramArtifact entries.
        """
        bundle = PatternDiagramBundle(pattern_name=pattern_name)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _gen_one(strategy: str, phase: str, phase_text: str):
            """Generate one diagram with concurrency limit and timeout."""
            async with semaphore:
                try:
                    coro = asyncio.to_thread(
                        self._generate_single_diagram,
                        pattern_name, services, strategy,
                        phase, phase_text, pattern_context,
                    )
                    artifact = await asyncio.wait_for(
                        coro, timeout=timeout_per_diagram
                    )
                    return strategy, phase, artifact
                except asyncio.TimeoutError:
                    logger.error(
                        f"Diagram generation timed-out for {strategy}/{phase}"
                    )
                    fallback = DiagramArtifact(
                        dr_strategy=strategy,
                        lifecycle_phase=phase,
                        svg_content=self._fallback_svg(strategy, phase, services),
                        drawio_xml=self._fallback_drawio(strategy, phase, services),
                        is_fallback=True,
                        description=phase_text,
                    )
                    fallback.png_bytes = self._svg_to_png(fallback.svg_content)
                    return strategy, phase, fallback
                except Exception as e:
                    logger.error(
                        f"Diagram generation failed for {strategy}/{phase}: {e}"
                    )
                    fallback = DiagramArtifact(
                        dr_strategy=strategy,
                        lifecycle_phase=phase,
                        svg_content=self._fallback_svg(strategy, phase, services),
                        drawio_xml=self._fallback_drawio(strategy, phase, services),
                        is_fallback=True,
                        description=phase_text,
                    )
                    fallback.png_bytes = self._svg_to_png(fallback.svg_content)
                    return strategy, phase, fallback

        # Build task list for all 12 combinations
        tasks = []
        for strategy in DR_STRATEGIES:
            strategy_text = hadr_text_sections.get(strategy, "")
            phase_texts = self._split_phases(strategy_text)
            for phase in LIFECYCLE_PHASES:
                phase_text = phase_texts.get(phase, "")
                logger.info(f"Scheduling async diagram: {strategy} / {phase}")
                tasks.append(_gen_one(strategy, phase, phase_text))

        # Execute all (up to max_concurrent at a time)
        results = await asyncio.gather(*tasks, return_exceptions=False)

        for strategy, phase, artifact in results:
            bundle.diagrams[(strategy, phase)] = artifact

        total = len(bundle.diagrams)
        fallbacks = sum(1 for a in bundle.all_artifacts() if a.is_fallback)
        logger.info(
            f"Async generated {total} diagrams for '{pattern_name}' "
            f"({fallbacks} fallbacks)"
        )
        return bundle

    # ─── Single diagram generation ───────────────────────────────────────

    def _generate_single_diagram(
        self,
        pattern_name: str,
        services: List[str],
        dr_strategy: str,
        lifecycle_phase: str,
        phase_description: str,
        pattern_context: Dict[str, Any],
    ) -> DiagramArtifact:
        """Generate SVG + draw.io XML for one (strategy, phase) pair."""
        artifact = DiagramArtifact(
            dr_strategy=dr_strategy,
            lifecycle_phase=lifecycle_phase,
        )

        if not self.model:
            logger.error("Model not available; returning fallback diagram")
            artifact.svg_content = self._fallback_svg(
                dr_strategy, lifecycle_phase, services
            )
            artifact.drawio_xml = self._fallback_drawio(
                dr_strategy, lifecycle_phase, services
            )
            artifact.is_fallback = True
            artifact.description = phase_description
            artifact.png_bytes = self._svg_to_png(artifact.svg_content)
            return artifact

        # ── 1. Generate SVG ──────────────────────────────────────────────
        svg_content = self._generate_svg(
            pattern_name, services, dr_strategy,
            lifecycle_phase, phase_description, pattern_context,
        )
        valid_svg, svg_content = self._validate_and_fix_svg(svg_content)
        if not valid_svg:
            # One retry with explicit error feedback
            logger.warning(f"SVG invalid for {dr_strategy}/{lifecycle_phase}, retrying…")
            svg_content = self._generate_svg(
                pattern_name, services, dr_strategy,
                lifecycle_phase, phase_description, pattern_context,
                retry_hint="Previous SVG was malformed. Ensure valid XML with xmlns and viewBox.",
            )
            valid_svg, svg_content = self._validate_and_fix_svg(svg_content)
            if not valid_svg:
                logger.error(f"SVG retry failed for {dr_strategy}/{lifecycle_phase}")
                svg_content = self._fallback_svg(dr_strategy, lifecycle_phase, services)
                artifact.is_fallback = True

        artifact.svg_content = svg_content

        # ── 2. Generate draw.io XML ──────────────────────────────────────
        drawio_xml = self._generate_drawio(
            pattern_name, services, dr_strategy,
            lifecycle_phase, phase_description, pattern_context,
        )
        artifact.drawio_xml = drawio_xml

        # ── 3. Convert SVG → PNG ─────────────────────────────────────────
        artifact.png_bytes = self._svg_to_png(svg_content)

        # ── 4. Store description ─────────────────────────────────────────
        artifact.description = phase_description

        return artifact

    # ─── SVG generation via Gemini ───────────────────────────────────────

    def _generate_svg(
        self,
        pattern_name: str,
        services: List[str],
        dr_strategy: str,
        lifecycle_phase: str,
        phase_description: str,
        pattern_context: Dict[str, Any],
        retry_hint: str = "",
    ) -> str:
        """Ask Gemini to produce an SVG component diagram."""
        services_list = "\n".join(f"  - {s}" for s in services)
        state_guide = self._state_guide(dr_strategy, lifecycle_phase)

        prompt = f"""
Generate a clean, professional SVG component diagram for the following HA/DR scenario.

# Pattern
Name: {pattern_name}
Services:
{services_list}

# DR Strategy: {dr_strategy}
# Lifecycle Phase: {lifecycle_phase}

# Phase Description
{phase_description if phase_description else "(Generate appropriate component states based on the DR strategy and lifecycle phase.)"}

# State Guide
{state_guide}

# Colour Palette for Service States
{json.dumps(STATE_COLORS, indent=2)}

# Layout Rules
1. Show TWO regions side-by-side: "Primary Region" (left, light-blue background)
   and "DR Region" (right, light-orange background).
2. Inside each region, draw a rounded rectangle for EVERY service in the pattern.
3. Colour each service box using the state colour from the palette above.
4. Below or inside each box, show the service state label (Active, Standby, etc.).
5. Draw arrows between Primary and DR service pairs to show data replication,
   failover direction, or synchronisation — label the arrow with the mechanism
   (e.g., "Cross-Region Replication", "Route 53 Failover", "Backup→Restore").
6. Include a title at the top: "{dr_strategy} — {lifecycle_phase}".
7. Include a legend in the bottom-right corner mapping colours to states.
8. Use viewBox="0 0 900 600" and width="900" height="600".
9. Ensure valid SVG with xmlns="http://www.w3.org/2000/svg".

# One-Shot Example
{SVG_ONE_SHOT_EXAMPLE}

{f"# IMPORTANT: {retry_hint}" if retry_hint else ""}

Output ONLY the raw SVG markup. Do NOT wrap it in markdown code fences.
Start with <svg and end with </svg>.
"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )
            return self._strip_code_fences(response.text.strip())
        except Exception as e:
            logger.error(f"SVG generation failed: {e}")
            return ""

    # ─── draw.io XML generation via Gemini ───────────────────────────────

    def _generate_drawio(
        self,
        pattern_name: str,
        services: List[str],
        dr_strategy: str,
        lifecycle_phase: str,
        phase_description: str,
        pattern_context: Dict[str, Any],
    ) -> str:
        """Ask Gemini to produce draw.io-compatible XML."""
        services_list = "\n".join(f"  - {s}" for s in services)
        state_guide = self._state_guide(dr_strategy, lifecycle_phase)

        prompt = f"""
Generate a draw.io XML file (mxfile format) for the following HA/DR component diagram.

# Pattern
Name: {pattern_name}
Services:
{services_list}

# DR Strategy: {dr_strategy}
# Lifecycle Phase: {lifecycle_phase}

# Phase Description
{phase_description if phase_description else "(Generate appropriate states based on DR strategy and lifecycle phase.)"}

# State Guide
{state_guide}

# Colour Palette for Service States
{json.dumps(STATE_COLORS, indent=2)}

# Layout Rules
1. Two container shapes side-by-side: "Primary Region" (fillColor=#dae8fc)
   and "DR Region" (fillColor=#fff2cc).
2. Inside each container, add a rounded-rectangle cell for each service.
3. Colour each service cell with the appropriate state colour from the palette.
4. Include the service name and state in the cell value, e.g.
   "Amazon RDS&#10;[Active]" (use &#10; for newline in draw.io values).
5. Add edge cells between Primary ↔ DR service pairs showing the
   replication/failover mechanism as a label.
6. Set the diagram name to "{dr_strategy} - {lifecycle_phase}".

# One-Shot Example
{DRAWIO_ONE_SHOT_EXAMPLE}

Output ONLY the raw XML. Do NOT wrap it in markdown code fences.
Start with <?xml or <mxfile and end with </mxfile>.
"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )
            xml_text = self._strip_code_fences(response.text.strip())
            # Basic validation: must contain <mxfile
            if "<mxfile" not in xml_text:
                logger.warning("draw.io XML missing <mxfile> — using fallback")
                return self._fallback_drawio(dr_strategy, lifecycle_phase, services)
            return xml_text
        except Exception as e:
            logger.error(f"draw.io generation failed: {e}")
            return self._fallback_drawio(dr_strategy, lifecycle_phase, services)

    # ─── SVG validation & fix ────────────────────────────────────────────

    @staticmethod
    def _validate_and_fix_svg(svg: str) -> Tuple[bool, str]:
        """
        Parse SVG with ElementTree and attempt auto-fixes for common issues.
        Returns (is_valid, possibly_fixed_svg).
        """
        if not svg or not svg.strip():
            return False, svg

        # Strip any stray content before <svg
        svg_start = svg.find("<svg")
        if svg_start > 0:
            svg = svg[svg_start:]
        svg_end = svg.rfind("</svg>")
        if svg_end > 0:
            svg = svg[: svg_end + len("</svg>")]

        # Ensure xmlns
        if 'xmlns="http://www.w3.org/2000/svg"' not in svg:
            svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)

        # Ensure viewBox exists
        if "viewBox" not in svg:
            svg = svg.replace(
                "<svg",
                '<svg viewBox="0 0 900 600"',
                1,
            )

        try:
            ET.fromstring(svg.encode("utf-8"))
            return True, svg
        except ET.ParseError as e:
            logger.warning(f"SVG parse error: {e}")
            return False, svg

    # ─── SVG → PNG conversion ────────────────────────────────────────────

    @staticmethod
    def _svg_to_png(svg_content: str) -> bytes:
        """
        Convert SVG string to PNG bytes.

        Uses svglib + reportlab with a pycairo shim so it works on all
        platforms (Windows, Linux, macOS) without requiring the native
        ``libcairo`` shared library to be installed separately.

        Falls back to cairosvg if svglib is unavailable (e.g. on Linux
        containers where native Cairo is present).
        """
        if not svg_content:
            return b""

        # ── Approach 1: svglib + reportlab (pure-Python, cross-platform) ─
        try:
            # Shim: let rlPyCairo/cairocffi resolve via pycairo's bundled lib
            import cairo as _pycairo          # pycairo (bundles native DLLs)
            import sys as _sys
            if "cairocffi" not in _sys.modules:
                _sys.modules["cairocffi"] = _pycairo

            import tempfile
            import os
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM

            with tempfile.NamedTemporaryFile(
                suffix=".svg", delete=False, mode="w", encoding="utf-8"
            ) as tmp:
                tmp.write(svg_content)
                tmp_path = tmp.name

            try:
                drawing = svg2rlg(tmp_path)
                if drawing is None:
                    raise ValueError("svglib returned None — SVG may be invalid")
                png_bytes = renderPM.drawToString(drawing, fmt="PNG")
                return png_bytes
            finally:
                os.unlink(tmp_path)

        except Exception as svg_err:
            logger.warning(f"svglib SVG→PNG failed ({svg_err}), trying cairosvg…")

        # ── Approach 2: cairosvg (needs native libcairo — works in Linux) ─
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                output_width=900,
                output_height=600,
            )
            return png_bytes
        except ImportError:
            logger.warning(
                "Neither svglib nor cairosvg could convert SVG→PNG. "
                "Install with: pip install svglib reportlab pycairo"
            )
            return b""
        except Exception as e:
            logger.error(f"SVG→PNG conversion failed: {e}")
            return b""

    # ─── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences (```xml, ```svg, etc.) from LLM output."""
        # Remove opening fence
        text = re.sub(r"^```(?:xml|svg|html)?\s*\n?", "", text, flags=re.MULTILINE)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    @staticmethod
    def _state_guide(dr_strategy: str, lifecycle_phase: str) -> str:
        """
        Provide a short hint about expected service states for a given
        strategy × phase combination to help the LLM produce correct diagrams.
        """
        guides = {
            ("Backup and Restore", "Initial Provisioning"):
                "Primary: all services Active. DR: all services Not-Deployed. "
                "Backups stored in cross-region storage.",
            ("Backup and Restore", "Failover"):
                "Primary: all services down/unavailable. DR: services being "
                "Restored from backups. Show Restoring state.",
            ("Backup and Restore", "Failback"):
                "DR: services Active. Primary: services being Restored/Syncing "
                "back. Show data sync direction DR→Primary.",
            ("Pilot Light On Demand", "Initial Provisioning"):
                "Primary: all Active. DR: core services (DB, config) in minimal "
                "Standby; compute services Not-Deployed.",
            ("Pilot Light On Demand", "Failover"):
                "Primary: down. DR: core services promoted to Active; compute "
                "services being provisioned (Restoring).",
            ("Pilot Light On Demand", "Failback"):
                "DR: Active. Primary: services being re-provisioned and Syncing.",
            ("Pilot Light Cold Standby", "Initial Provisioning"):
                "Primary: all Active. DR: core services in Cold Standby "
                "(stopped but deployed); compute Not-Deployed or Scaled-Down.",
            ("Pilot Light Cold Standby", "Failover"):
                "Primary: down. DR: core services started → Active; compute "
                "services started → Active. Longer spin-up than Warm Standby.",
            ("Pilot Light Cold Standby", "Failback"):
                "DR: Active. Primary: services being restarted and data Syncing.",
            ("Warm Standby", "Initial Provisioning"):
                "Primary: all Active. DR: all services running at Scaled-Down "
                "capacity (Standby). Active replication in progress.",
            ("Warm Standby", "Failover"):
                "Primary: down. DR: all services scaled UP to Active (full "
                "capacity). DNS/routing switched to DR.",
            ("Warm Standby", "Failback"):
                "DR: Active. Primary: services restarted and Syncing. "
                "Once synced, traffic shifted back to Primary.",
        }
        return guides.get(
            (dr_strategy, lifecycle_phase),
            "Use your best judgement for the expected service states."
        )

    @staticmethod
    def _split_phases(strategy_text: str) -> Dict[str, str]:
        """
        Split a DR strategy Markdown section into per-phase text blocks
        by matching ### headings for each lifecycle phase.
        """
        result: Dict[str, str] = {}
        if not strategy_text:
            return result

        # Build regex to find phase headings
        phase_names = "|".join(re.escape(p) for p in LIFECYCLE_PHASES)
        pattern = re.compile(
            rf"(###\s*(?:{phase_names}))", re.IGNORECASE
        )
        parts = pattern.split(strategy_text)

        # parts will be [pre_text, heading1, body1, heading2, body2, ...]
        i = 1
        while i < len(parts) - 1:
            heading = parts[i].strip().lstrip("#").strip()
            body = parts[i + 1].strip()
            # Match heading to canonical phase name
            for phase in LIFECYCLE_PHASES:
                if phase.lower() in heading.lower():
                    result[phase] = body
                    break
            i += 2

        return result

    # ─── Fallback generators ─────────────────────────────────────────────

    @staticmethod
    def _fallback_svg(
        dr_strategy: str, lifecycle_phase: str, services: List[str]
    ) -> str:
        """Generate a minimal placeholder SVG when Gemini output is invalid."""
        svc_boxes = []
        y = 120
        for svc in services[:8]:  # cap at 8 to fit
            svc_boxes.append(
                f'  <rect x="60" y="{y}" width="280" height="40" rx="6" fill="#BDBDBD"/>\n'
                f'  <text x="200" y="{y + 25}" text-anchor="middle" '
                f'font-family="Arial" font-size="12" fill="#fff">{svc}</text>'
            )
            y += 55
        boxes_str = "\n".join(svc_boxes)

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="900" height="600">
  <rect width="900" height="600" fill="#FAFAFA" rx="4"/>
  <text x="450" y="40" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#333">
    {dr_strategy} — {lifecycle_phase}
  </text>
  <text x="450" y="70" text-anchor="middle" font-family="Arial" font-size="13" fill="#999">
    (Placeholder — diagram generation failed; please recreate in draw.io)
  </text>
  <rect x="30" y="90" width="400" height="{y - 60}" rx="10" fill="#E3F2FD" stroke="#1565C0" stroke-width="1.5"/>
  <text x="230" y="112" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#333">Primary Region</text>
{boxes_str}
  <rect x="470" y="90" width="400" height="{y - 60}" rx="10" fill="#FFF3E0" stroke="#E65100" stroke-width="1.5"/>
  <text x="670" y="112" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#333">DR Region</text>
</svg>"""

    @staticmethod
    def _fallback_drawio(
        dr_strategy: str, lifecycle_phase: str, services: List[str]
    ) -> str:
        """Generate a minimal placeholder draw.io XML."""
        cells = []
        cell_id = 10
        y_pos = 100

        for svc in services[:8]:
            cells.append(
                f'        <mxCell id="{cell_id}" value="{svc}&#10;[Unknown]" '
                f'style="rounded=1;whiteSpace=wrap;fillColor=#BDBDBD;fontColor=#ffffff;'
                f'strokeColor=#757575;" vertex="1" parent="1">\n'
                f'          <mxGeometry x="60" y="{y_pos}" width="160" height="45" as="geometry"/>\n'
                f'        </mxCell>'
            )
            cell_id += 1
            y_pos += 60

        cells_str = "\n".join(cells)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io">
  <diagram name="{dr_strategy} - {lifecycle_phase}" id="fallback">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Primary Region" style="rounded=1;whiteSpace=wrap;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="30" y="50" width="350" height="{y_pos + 20}" as="geometry"/>
        </mxCell>
{cells_str}
        <mxCell id="100" value="DR Region" style="rounded=1;whiteSpace=wrap;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="420" y="50" width="350" height="{y_pos + 20}" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
