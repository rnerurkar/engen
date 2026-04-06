"""
HA/DR Documentation Generator
------------------------------
Generates the HA/DR sections of a pattern document using:
  1. Service-level HA/DR reference docs (from Vertex AI Search via ServiceHADRRetriever)
  2. The donor pattern's HA/DR sections (one-shot example)
  3. The new pattern's component specification and architecture description

Generates ONE DR strategy section at a time for prompt focus and easier
retry on failure.

Provides both sync (``generate_hadr_sections``) and async
(``agenerate_hadr_sections``) entry-points so the caller can choose
whether to parallelise across strategies.
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

logger = logging.getLogger(__name__)


class HADRDocumentationGenerator:
    """
    Generates pattern-level HA/DR documentation sections using:
      - Donor pattern HA/DR sections as one-shot structural examples
      - Service-level HA/DR docs as factual building blocks
      - The new pattern's component specification for context
    """

    # Must match ServiceHADRRetriever.DR_STRATEGIES exactly
    DR_STRATEGIES = [
        "Backup and Restore",
        "Pilot Light On Demand",
        "Pilot Light Cold Standby",
        "Warm Standby",
    ]

    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self._init_vertex_ai()

    def _init_vertex_ai(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                "gemini-1.5-pro-preview-0409",
                system_instruction=(
                    "You are a Principal Cloud Architect specialising in "
                    "High Availability and Disaster Recovery for enterprise "
                    "cloud patterns."
                ),
            )
        except Exception as e:
            logger.error(f"Failed to initialise Vertex AI: {e}")
            self.model = None

    # ─── Prompt builder ──────────────────────────────────────────────────

    @staticmethod
    def _build_hadr_prompt(
        dr_strategy: str,
        donor_hadr_section: str,
        service_hadr_docs: Dict[str, List[Dict[str, Any]]],
        pattern_context: Dict[str, Any],
    ) -> str:
        """
        Build the prompt for generating ONE DR strategy section.

        We generate one strategy at a time so the LLM can focus on accuracy
        within the context window and individual sections can be retried
        independently.
        """
        # Build per-service reference blocks
        svc_ref_blocks: List[str] = []
        svc_diagram_blocks: List[str] = []
        for svc_name, chunks in service_hadr_docs.items():
            chunk_texts = "\n".join(
                c.get("content", "") for c in chunks if c.get("content")
            )
            if chunk_texts:
                svc_ref_blocks.append(
                    f"### Service: {svc_name}\n{chunk_texts}"
                )

            # Collect diagram descriptions from chunks for this service
            diagrams_for_svc: List[str] = []
            for c in chunks:
                for desc in c.get("diagram_descriptions", []):
                    if desc and desc not in diagrams_for_svc:
                        diagrams_for_svc.append(desc)
            if diagrams_for_svc:
                svc_diagram_blocks.append(
                    f"### Service: {svc_name}\n"
                    + "\n".join(
                        f"- Diagram: {d}" for d in diagrams_for_svc
                    )
                )

        service_references = (
            "\n\n".join(svc_ref_blocks)
            if svc_ref_blocks
            else "(No service-level references available)"
        )

        service_diagram_section = ""
        if svc_diagram_blocks:
            service_diagram_section = (
                "\n# Service-Level HA/DR Diagram Descriptions\n"
                "The following are AI-generated descriptions of the reference\n"
                "HA/DR architecture diagrams from the service-level documentation.\n"
                "Use these as VISUAL CONTEXT when writing the narrative — they show\n"
                "what the architecture looks like at each lifecycle phase. Your text\n"
                "should be consistent with these diagram descriptions.\n\n"
                + "\n\n".join(svc_diagram_blocks)
            )

        pattern_summary = json.dumps(pattern_context, indent=2)

        return f"""
# Role & Objective
You are a Principal Cloud Architect specialising in High Availability and
Disaster Recovery. 

Task: Write the "{dr_strategy}" section of a pattern-level HA/DR document.

# Important Context
You are writing for a NEW pattern. The new pattern uses multiple services
together. Your job is to describe how the ENTIRE PATTERN (not individual
services) behaves under this DR strategy during three lifecycle phases:
Initial Provisioning, Failover, and Failback.

# Instructions
1. Read the DONOR PATTERN EXAMPLE below. This is a REAL approved HA/DR
   section from a similar pattern. Use it as a **structural and stylistic
   template**. Match its tone, depth, and format.
2. Read the SERVICE-LEVEL HA/DR REFERENCES below. These describe how EACH
   individual service behaves under "{dr_strategy}". Use these as **factual
   building blocks**.
3. **SYNTHESISE**: Combine the service-level behaviours into a coherent
   pattern-level narrative:
   - Initial Provisioning: what gets deployed in primary and DR regions.
   - Failover: the sequence of events across ALL services. Which service
     fails over first? What triggers the next? Expected RTO/RPO.
   - Failback: how to restore to the primary region. What order? What
     data synchronisation is needed?
4. DO NOT copy the donor pattern verbatim — the new pattern has DIFFERENT
   services.
5. DO NOT contradict the service-level references. If a service does not
   support automatic failover under this strategy, say so.
6. Include a brief summary table at the end of each phase listing each
   service and its state (Active, Standby, Scaled-Down, Not-Deployed, etc.)

# New Pattern Context
{pattern_summary}

# Donor Pattern Example (One-Shot)
## {dr_strategy}
{donor_hadr_section if donor_hadr_section else "(No donor example available for this strategy — generate based on service references and best practices.)"}

# Service-Level HA/DR References
{service_references}
{service_diagram_section}

# Output Format
Write in clean Markdown. Use these exact sub-headings:

## {dr_strategy}

### Initial Provisioning
(content — describe the component architecture: which services are deployed
in each region, their state, replication mechanisms, and how the initial
setup looks. This description accompanies a component diagram that will be
generated separately, so be specific about service states and connections.)

| Service | Primary Region State | DR Region State |
|---------|---------------------|-----------------|
| ...     | ...                 | ...             |

### Failover
(content — describe the failover sequence step by step: what triggers it,
which services fail over first, dependencies, expected RTO/RPO. Be specific
about each service's state transition as this accompanies a component diagram.)

| Service | Pre-Failover State | Post-Failover State | Failover Mechanism |
|---------|-------------------|--------------------|--------------------|
| ...     | ...               | ...                | ...                |

### Failback
(content — describe the failback sequence: how services are restored to the
primary region, data synchronisation requirements, order of operations. Be
specific about state transitions as this accompanies a component diagram.)

| Service | Pre-Failback State | Post-Failback State | Sync Required |
|---------|--------------------|--------------------|---------------|
| ...     | ...                | ...                | ...           |
"""

    # ─── Generation entry-point ──────────────────────────────────────────

    def generate_hadr_sections(
        self,
        pattern_context: Dict[str, Any],
        donor_hadr_sections: Dict[str, str],
        service_hadr_docs: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ) -> Dict[str, str]:
        """
        Generate all four DR strategy sections for a new pattern document.

        Args:
            pattern_context:      The new pattern's component spec +
                                  architecture description.
            donor_hadr_sections:  DR strategy name → donor pattern's text
                                  for that strategy.
            service_hadr_docs:    Output of
                                  ``ServiceHADRRetriever.retrieve_all_services_hadr()``.
                                  Nested: service_name → dr_strategy → [chunks]

        Returns:
            Dict mapping DR strategy name → generated Markdown section.
        """
        if not self.model:
            logger.error("Vertex AI model not initialised — cannot generate HA/DR docs")
            return {
                s: f"## {s}\n\n*Model not available — section not generated.*"
                for s in self.DR_STRATEGIES
            }

        generated_sections: Dict[str, str] = {}

        for strategy in self.DR_STRATEGIES:
            logger.info(f"Generating HA/DR section: {strategy}")

            # Gather service-level docs for THIS strategy across all services
            per_service_for_strategy: Dict[str, List[Dict[str, Any]]] = {}
            for svc_name, strategy_map in service_hadr_docs.items():
                chunks = strategy_map.get(strategy, [])
                if chunks:
                    per_service_for_strategy[svc_name] = chunks

            # Donor pattern section for this strategy
            donor_section = donor_hadr_sections.get(strategy, "")
            if not donor_section:
                logger.warning(
                    f"No donor example for '{strategy}' — generating without one-shot."
                )

            prompt = self._build_hadr_prompt(
                dr_strategy=strategy,
                donor_hadr_section=donor_section,
                service_hadr_docs=per_service_for_strategy,
                pattern_context=pattern_context,
            )

            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=4096,
                    ),
                )
                generated_sections[strategy] = response.text.strip()
                logger.info(
                    f"Generated {len(response.text)} chars for '{strategy}'"
                )
            except Exception as e:
                logger.error(f"HA/DR generation failed for '{strategy}': {e}")
                generated_sections[strategy] = (
                    f"## {strategy}\n\n"
                    f"*Generation failed ({e}). Please complete manually.*"
                )

        return generated_sections

    # ─── Async generation entry-point ────────────────────────────────────

    async def agenerate_hadr_sections(
        self,
        pattern_context: Dict[str, Any],
        donor_hadr_sections: Dict[str, str],
        service_hadr_docs: Dict[str, Dict[str, List[Dict[str, Any]]]],
        timeout_per_strategy: float = 120.0,
    ) -> Dict[str, str]:
        """
        Async version of ``generate_hadr_sections`` — generates all four
        DR-strategy sections **in parallel** via ``asyncio.gather``.

        Each Gemini ``generate_content`` call is offloaded to a thread so
        the event loop is never blocked.

        Args:
            pattern_context:          Same as sync version.
            donor_hadr_sections:      Same as sync version.
            service_hadr_docs:        Same as sync version.
            timeout_per_strategy:     Max seconds per strategy LLM call
                                      (default 120 s).

        Returns:
            Dict mapping DR strategy name → generated Markdown section.
        """
        if not self.model:
            logger.error("Vertex AI model not initialised — cannot generate HA/DR docs")
            return {
                s: f"## {s}\n\n*Model not available — section not generated.*"
                for s in self.DR_STRATEGIES
            }

        # ── Build prompts (CPU-only, no I/O) ─────────────────────────────
        strategy_prompts: Dict[str, str] = {}
        for strategy in self.DR_STRATEGIES:
            per_service_for_strategy: Dict[str, List[Dict[str, Any]]] = {}
            for svc_name, strategy_map in service_hadr_docs.items():
                chunks = strategy_map.get(strategy, [])
                if chunks:
                    per_service_for_strategy[svc_name] = chunks

            donor_section = donor_hadr_sections.get(strategy, "")
            if not donor_section:
                logger.warning(
                    f"No donor example for '{strategy}' — generating without one-shot."
                )

            strategy_prompts[strategy] = self._build_hadr_prompt(
                dr_strategy=strategy,
                donor_hadr_section=donor_section,
                service_hadr_docs=per_service_for_strategy,
                pattern_context=pattern_context,
            )

        # ── Fire all four LLM calls in parallel ─────────────────────────
        async def _gen_one(strategy: str, prompt: str) -> str:
            """Generate one strategy section with timeout."""
            try:
                coro = asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=4096,
                    ),
                )
                response = await asyncio.wait_for(coro, timeout=timeout_per_strategy)
                logger.info(f"Generated {len(response.text)} chars for '{strategy}'")
                return response.text.strip()
            except asyncio.TimeoutError:
                logger.error(f"HA/DR generation timed-out for '{strategy}'")
                return (
                    f"## {strategy}\n\n"
                    f"*Generation timed out after {timeout_per_strategy}s. "
                    f"Please complete manually.*"
                )
            except Exception as e:
                logger.error(f"HA/DR generation failed for '{strategy}': {e}")
                return (
                    f"## {strategy}\n\n"
                    f"*Generation failed ({e}). Please complete manually.*"
                )

        tasks = [
            _gen_one(strategy, strategy_prompts[strategy])
            for strategy in self.DR_STRATEGIES
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        generated_sections: Dict[str, str] = {}
        for strategy, text in zip(self.DR_STRATEGIES, results):
            generated_sections[strategy] = text

        return generated_sections

    # ─── Donor-pattern parsing helper ────────────────────────────────────

    @staticmethod
    def extract_donor_hadr_sections(donor_html_content: str) -> Dict[str, str]:
        """
        Parse the donor pattern's HTML/Markdown content and extract
        HA/DR sub-sections keyed by DR strategy name.

        Looks for headings matching the DR strategy names and captures
        everything up to the next strategy heading or end of content.
        """
        # Build a combined pattern that matches any strategy heading
        strategy_names = HADRDocumentationGenerator.DR_STRATEGIES
        # Escape for regex
        escaped = [re.escape(s) for s in strategy_names]
        # Match markdown ## headings or HTML <h2>/<h3> tags
        heading_re = re.compile(
            r"(?:^#{1,3}\s*|<h[23][^>]*>)"
            r"("
            + "|".join(escaped)
            + r")"
            r"(?:\s*</h[23]>)?",
            re.IGNORECASE | re.MULTILINE,
        )

        sections: Dict[str, str] = {}
        matches = list(heading_re.finditer(donor_html_content))

        for i, match in enumerate(matches):
            strategy_name = match.group(1).strip()
            # Normalise to the canonical list
            canonical = None
            for s in strategy_names:
                if s.lower() == strategy_name.lower():
                    canonical = s
                    break
            if not canonical:
                continue

            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(donor_html_content)
            sections[canonical] = donor_html_content[start:end].strip()

        # Fill missing strategies with empty string
        for s in strategy_names:
            if s not in sections:
                sections[s] = ""

        return sections
