"""
Pattern Synthesis sub-package
-----------------------------
Exports the core classes used by the orchestrator for:
  - HA/DR documentation generation, validation, and diagram storage
  - Component specification extraction
  - Artifact (IaC / boilerplate) generation and validation
"""

from core.pattern_synthesis.service_hadr_retriever import ServiceHADRRetriever
from core.pattern_synthesis.hadr_generator import HADRDocumentationGenerator
from core.pattern_synthesis.hadr_diagram_generator import (
    HADRDiagramGenerator,
    DiagramArtifact,
    PatternDiagramBundle,
    DRAWIO_SERVICE_ICONS,
    get_drawio_icon_style,
)
from core.pattern_synthesis.hadr_diagram_storage import HADRDiagramStorage
from core.pattern_synthesis.component_specification import ComponentSpecification
from core.pattern_synthesis.artifact_generator import ArtifactGenerator
from core.pattern_synthesis.artifact_validator import ArtifactValidator

__all__ = [
    "ServiceHADRRetriever",
    "HADRDocumentationGenerator",
    "HADRDiagramGenerator",
    "DiagramArtifact",
    "PatternDiagramBundle",
    "DRAWIO_SERVICE_ICONS",
    "get_drawio_icon_style",
    "HADRDiagramStorage",
    "ComponentSpecification",
    "ArtifactGenerator",
    "ArtifactValidator",
]
