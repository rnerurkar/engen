"""
Pattern Synthesis — HA/DR sub-package
-------------------------------------
Exports the core HA/DR classes used by the orchestrator to generate,
validate, and store pattern-level HA/DR documentation and diagrams.
"""

from core.pattern_synthesis.service_hadr_retriever import ServiceHADRRetriever
from core.pattern_synthesis.hadr_generator import HADRDocumentationGenerator
from core.pattern_synthesis.hadr_diagram_generator import (
    HADRDiagramGenerator,
    DiagramArtifact,
    PatternDiagramBundle,
)
from core.pattern_synthesis.hadr_diagram_storage import HADRDiagramStorage

__all__ = [
    "ServiceHADRRetriever",
    "HADRDocumentationGenerator",
    "HADRDiagramGenerator",
    "DiagramArtifact",
    "PatternDiagramBundle",
    "HADRDiagramStorage",
]
