"""recommend_architecture — the full reasoning pipeline.

Chains (per architecture, lines 209-214):
  validate_spec (deterministic signal extraction) ->
  retrieve (RAG: search_patterns + search_skills + discover_integrations) ->
  invoke_llm_agent (authored 8-step system prompt on Gemini) ->
  parse_selections -> ArchitectureSelections

Everything EXCEPT the model's reasoning is implemented and tested. The single live seam
is the Gemini call inside invoke_llm_agent (inject model_fn in tests; bind ADK LlmAgent live).

Spec/plan are passed AS MARKDOWN throughout — never converted to JSON (architecture-faithful).
"""
from __future__ import annotations

import os
import sys
from collections.abc import Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from assembly.selections import ArchitectureSelections
from clients.apigee_hub import ApigeeHubClient
from clients.vertex_search import VertexSearchClient
from reasoning.llm_harness import (
    RetrievedContext,
    build_user_message,
    invoke_llm_agent,
    load_system_prompt,
    parse_selections,
)
from reasoning.validate_spec import SpecValidation, validate_spec


class SpecBlockedError(Exception):
    """Raised when validate_spec returns a BLOCK status — blueprint_start returns guidance."""
    def __init__(self, validation: SpecValidation):
        self.validation = validation
        msgs = [f.guidance for f in validation.findings if f.status == "BLOCK"]
        super().__init__("; ".join(msgs))


class RecommendArchitecture:
    def __init__(self):
        self.search = VertexSearchClient()
        self.api_hub = ApigeeHubClient()

    def retrieve(self, signals) -> RetrievedContext:
        """RAG retrieval (search_patterns + search_skills) + API Hub discovery.
        Returns empty until the corpus is populated; orchestration is real."""
        patterns = self.search.search_patterns(signals.ordering_words)
        skills = self.search.search_tools(signals.data_systems)  # skill catalog query
        integrations = []  # discover_integrations() — API Hub query (TODO live; returns [])
        return RetrievedContext(patterns=patterns, skills=skills, integrations=integrations)

    def run(self, spec_md: str, plan_md: str,
            model_fn: Callable[[str, str], dict] | None = None) -> ArchitectureSelections:
        """Full pipeline: validate -> retrieve -> reason -> parse selections.

        model_fn injects the model in tests; in production it wraps the live ADK LlmAgent.
        """
        # Step 0: validate_spec (deterministic quality gate)
        validation = validate_spec(spec_md)
        if validation.blocked:
            raise SpecBlockedError(validation)

        # Step 1: RAG + API Hub retrieval
        ctx = self.retrieve(validation.signals)

        # Step 2: invoke the authored-prompt LlmAgent
        system_prompt = load_system_prompt()
        signals_dict = {
            "ordering_words": validation.signals.ordering_words,
            "own_system_partners": validation.signals.own_system_partners,
            "measurable_criteria": validation.signals.measurable_criteria,
            "data_systems": validation.signals.data_systems,
            "spec_quality_score": validation.quality_score,
        }
        user_message = build_user_message(spec_md, plan_md, signals_dict, ctx)
        model_output = invoke_llm_agent(system_prompt, user_message, model_fn=model_fn)

        # Step 3: parse into validated selections (feeds assemble_blueprint)
        return parse_selections(model_output)
