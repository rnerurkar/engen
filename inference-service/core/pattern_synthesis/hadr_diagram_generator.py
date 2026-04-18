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


@dataclass
class RegionStates:
    """Service states for a given (DR strategy, lifecycle phase) pair."""
    primary_core: str       # State of data/storage services in primary region
    primary_non_core: str   # State of compute/network services in primary region
    dr_core: str            # State of data/storage services in DR region
    dr_non_core: str        # State of compute/network services in DR region
    arrow_label: str        # Label for the cross-region replication/failover arrow


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

# ──────────────────────────────────────────────────────────────────────────────
# Structured state matrix for programmatic diagram generation
#
# Maps every (DR strategy, lifecycle phase) pair to the expected service
# states in the Primary and DR regions.  "Core" = databases & persistent
# storage (stateful); "non-core" = compute, networking, messaging (stateless).
# ──────────────────────────────────────────────────────────────────────────────

STATE_MATRIX: Dict[Tuple[str, str], RegionStates] = {
    # ── Backup and Restore ────────────────────────────────────────────────
    ("Backup and Restore", "Initial Provisioning"): RegionStates(
        "Active", "Active", "Not-Deployed", "Not-Deployed",
        "Scheduled Backup \u2192 Cross-Region Storage"),
    ("Backup and Restore", "Failover"): RegionStates(
        "Not-Deployed", "Not-Deployed", "Restoring", "Restoring",
        "Restore from Backup"),
    ("Backup and Restore", "Failback"): RegionStates(
        "Syncing", "Syncing", "Active", "Active",
        "Data Sync DR \u2192 Primary"),
    # ── Pilot Light On Demand ─────────────────────────────────────────────
    ("Pilot Light On Demand", "Initial Provisioning"): RegionStates(
        "Active", "Active", "Standby", "Not-Deployed",
        "Async Replication"),
    ("Pilot Light On Demand", "Failover"): RegionStates(
        "Not-Deployed", "Not-Deployed", "Active", "Restoring",
        "Promote Replica"),
    ("Pilot Light On Demand", "Failback"): RegionStates(
        "Syncing", "Syncing", "Active", "Active",
        "Data Sync DR \u2192 Primary"),
    # ── Pilot Light Cold Standby ──────────────────────────────────────────
    ("Pilot Light Cold Standby", "Initial Provisioning"): RegionStates(
        "Active", "Active", "Standby", "Scaled-Down",
        "Async Replication"),
    ("Pilot Light Cold Standby", "Failover"): RegionStates(
        "Not-Deployed", "Not-Deployed", "Active", "Active",
        "Start + Promote"),
    ("Pilot Light Cold Standby", "Failback"): RegionStates(
        "Syncing", "Syncing", "Active", "Active",
        "Data Sync DR \u2192 Primary"),
    # ── Warm Standby ──────────────────────────────────────────────────────
    ("Warm Standby", "Initial Provisioning"): RegionStates(
        "Active", "Active", "Standby", "Scaled-Down",
        "Active Replication"),
    ("Warm Standby", "Failover"): RegionStates(
        "Not-Deployed", "Not-Deployed", "Active", "Active",
        "Scale Up + DNS Failover"),
    ("Warm Standby", "Failback"): RegionStates(
        "Syncing", "Syncing", "Active", "Active",
        "Data Sync DR \u2192 Primary"),
}

# Keywords that identify a service as "core" (stateful data layer).
# Everything else is classified as "non-core" (compute / network / messaging).
_CORE_SERVICE_KEYWORDS = frozenset({
    "rds", "aurora", "dynamodb", "elasticache", "neptune", "redshift",
    "sql", "spanner", "firestore", "bigtable", "bigquery", "memorystore",
    "s3", "efs", "ebs", "storage", "persistent disk", "filestore",
})


def _is_data_service(service_name: str) -> bool:
    """True if the service holds persistent state (database / storage)."""
    lower = service_name.lower()
    return any(kw in lower for kw in _CORE_SERVICE_KEYWORDS)

# ──────────────────────────────────────────────────────────────────────────────
# draw.io icon shape mapping  (AWS 4.0 + GCP shape libraries)
#
# When a service name matches a key (case-insensitive), the corresponding
# draw.io `style` fragment is injected so the diagram renders the official
# cloud-provider icon instead of a plain rectangle.
#
# Library references:
#   AWS:  mxgraph.aws4.*   (built-in to draw.io ≥ 20.x)
#   GCP:  mxgraph.gcp2.*   (built-in to draw.io ≥ 20.x)
# ──────────────────────────────────────────────────────────────────────────────

DRAWIO_SERVICE_ICONS: Dict[str, str] = {
    # ── AWS Services ──────────────────────────────────────────────────────
    # Compute
    "AWS Lambda":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.lambda;",
    "Amazon ECS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ecs;",
    "Amazon EKS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.eks;",
    "Amazon EC2":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ec2;",
    "AWS Fargate":             "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.fargate;",
    "AWS Step Functions":      "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.step_functions;",
    "AWS Batch":               "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.batch;",
    # Database
    "Amazon RDS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.rds;",
    "Amazon DynamoDB":         "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.dynamodb;",
    "Amazon Aurora":           "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.aurora;",
    "Amazon ElastiCache":      "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elasticache;",
    "Amazon Neptune":          "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.neptune;",
    "Amazon Redshift":         "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.redshift;",
    # Storage
    "Amazon S3":               "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.s3;",
    "Amazon EFS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_file_system;",
    "Amazon EBS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_block_store;",
    # Networking
    "Amazon VPC":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.vpc;",
    "Amazon CloudFront":       "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.cloudfront;",
    "Amazon Route 53":         "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.route_53;",
    "Elastic Load Balancer":   "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_load_balancing;",
    "Amazon API Gateway":      "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.api_gateway;",
    "AWS Global Accelerator":  "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.global_accelerator;",
    # Messaging
    "Amazon SQS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.sqs;",
    "Amazon SNS":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.sns;",
    "Amazon EventBridge":      "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.eventbridge;",
    "Amazon Kinesis":          "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.kinesis;",
    # Security & Management
    "AWS KMS":                 "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.key_management_service;",
    "AWS Secrets Manager":     "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.secrets_manager;",
    "AWS IAM":                 "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.identity_and_access_management;",
    "AWS WAF":                 "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.waf;",
    "AWS CloudWatch":          "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.cloudwatch;",
    "AWS CloudTrail":          "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.cloudtrail;",
    # CI/CD
    "AWS CodePipeline":        "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.codepipeline;",
    "Amazon ECR":              "shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ecr;",

    # ── GCP Services ─────────────────────────────────────────────────────
    # Compute
    "Cloud Run":               "shape=mxgraph.gcp2.cloud_run;",
    "Cloud Functions":         "shape=mxgraph.gcp2.cloud_functions;",
    "Compute Engine":          "shape=mxgraph.gcp2.compute_engine;",
    "Google Kubernetes Engine": "shape=mxgraph.gcp2.google_kubernetes_engine;",
    "GKE":                     "shape=mxgraph.gcp2.google_kubernetes_engine;",
    "App Engine":              "shape=mxgraph.gcp2.app_engine;",
    # Database
    "Cloud SQL":               "shape=mxgraph.gcp2.cloud_sql;",
    "Cloud Spanner":           "shape=mxgraph.gcp2.cloud_spanner;",
    "Firestore":               "shape=mxgraph.gcp2.cloud_firestore;",
    "Cloud Bigtable":          "shape=mxgraph.gcp2.cloud_bigtable;",
    "BigQuery":                "shape=mxgraph.gcp2.bigquery;",
    "Memorystore":             "shape=mxgraph.gcp2.cloud_memorystore;",
    # Storage
    "Cloud Storage":           "shape=mxgraph.gcp2.cloud_storage;",
    "Persistent Disk":         "shape=mxgraph.gcp2.persistent_disk;",
    "Filestore":               "shape=mxgraph.gcp2.filestore;",
    # Networking
    "Cloud CDN":               "shape=mxgraph.gcp2.cloud_cdn;",
    "Cloud DNS":               "shape=mxgraph.gcp2.cloud_dns;",
    "Cloud Load Balancing":    "shape=mxgraph.gcp2.cloud_load_balancing;",
    "Cloud Armor":             "shape=mxgraph.gcp2.cloud_armor;",
    "Cloud VPN":               "shape=mxgraph.gcp2.cloud_vpn;",
    "Cloud Interconnect":      "shape=mxgraph.gcp2.cloud_interconnect;",
    # Messaging
    "Cloud Pub/Sub":           "shape=mxgraph.gcp2.cloud_pubsub;",
    "Pub/Sub":                 "shape=mxgraph.gcp2.cloud_pubsub;",
    "Cloud Tasks":             "shape=mxgraph.gcp2.cloud_tasks;",
    "Eventarc":                "shape=mxgraph.gcp2.eventarc;",
    # Security & Management
    "Cloud KMS":               "shape=mxgraph.gcp2.cloud_key_management_service;",
    "Secret Manager":          "shape=mxgraph.gcp2.secret_manager;",
    "Cloud IAM":               "shape=mxgraph.gcp2.cloud_iam;",
    "Cloud Monitoring":        "shape=mxgraph.gcp2.cloud_monitoring;",
    "Cloud Logging":           "shape=mxgraph.gcp2.cloud_logging;",
    # CI/CD
    "Cloud Build":             "shape=mxgraph.gcp2.cloud_build;",
    "Artifact Registry":       "shape=mxgraph.gcp2.artifact_registry;",
    "Cloud Deploy":            "shape=mxgraph.gcp2.cloud_deploy;",
}

# Case-insensitive lookup helper
_ICON_LOOKUP: Dict[str, str] = {k.lower(): v for k, v in DRAWIO_SERVICE_ICONS.items()}


def get_drawio_icon_style(service_name: str) -> str:
    """Return the draw.io icon style fragment for *service_name*, or empty string."""
    return _ICON_LOOKUP.get(service_name.lower(), "")

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

# One-shot draw.io XML example (uses AWS icon shapes)
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
        <!-- Service: Amazon RDS (Active) — uses AWS RDS icon -->
        <mxCell id="3" value="Amazon RDS&#xa;[Active]" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.rds;whiteSpace=wrap;fillColor=#4CAF50;fontColor=#232F3E;strokeColor=#388E3C;fontStyle=1;fontSize=11;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;" vertex="1" parent="1">
          <mxGeometry x="80" y="100" width="60" height="60" as="geometry"/>
        </mxCell>
        <!-- State badge for Primary RDS -->
        <mxCell id="3b" value="Active" style="text;fontSize=10;fontStyle=2;fontColor=#388E3C;align=center;" vertex="1" parent="1">
          <mxGeometry x="70" y="165" width="80" height="18" as="geometry"/>
        </mxCell>
        <!-- DR Region container -->
        <mxCell id="4" value="DR Region" style="rounded=1;whiteSpace=wrap;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="420" y="50" width="350" height="400" as="geometry"/>
        </mxCell>
        <!-- Service: Amazon RDS (Not-Deployed) — uses AWS RDS icon -->
        <mxCell id="5" value="Amazon RDS&#xa;[Not-Deployed]" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.rds;whiteSpace=wrap;fillColor=#9E9E9E;fontColor=#232F3E;strokeColor=#757575;fontStyle=1;fontSize=11;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;opacity=50;" vertex="1" parent="1">
          <mxGeometry x="470" y="100" width="60" height="60" as="geometry"/>
        </mxCell>
        <!-- State badge for DR RDS -->
        <mxCell id="5b" value="Not-Deployed" style="text;fontSize=10;fontStyle=2;fontColor=#757575;align=center;" vertex="1" parent="1">
          <mxGeometry x="455" y="165" width="90" height="18" as="geometry"/>
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

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        use_ai_diagrams: bool = False,
        ai_model_name: str = "gemini-2.0-flash",
    ):
        """
        Args:
            project_id:       GCP project ID for Vertex AI.
            location:         GCP region.
            use_ai_diagrams:  When False (default), generates diagrams
                              programmatically — zero Gemini calls, zero
                              tokens, completes in < 1 second.  Set to True
                              to use AI for creative SVG layouts at the cost
                              of speed and tokens.
            ai_model_name:    Model to use when ``use_ai_diagrams=True``.
                              Defaults to ``gemini-2.0-flash`` (fast/cheap).
                              Change to ``gemini-2.5-pro`` only if quality
                              matters more than speed.
        """
        self.project_id = project_id
        self.location = location
        self.use_ai_diagrams = use_ai_diagrams
        self.ai_model_name = ai_model_name
        if self.use_ai_diagrams:
            self._init_model()
        else:
            self.model = None
            logger.info(
                "HADRDiagramGenerator initialised in programmatic mode "
                "(zero AI calls)"
            )

    def _init_model(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel(
                self.ai_model_name,
                system_instruction=(
                    "You are a Principal Cloud Architect and technical "
                    "illustrator. You generate accurate, clean SVG component "
                    "diagrams and draw.io XML files for enterprise HA/DR "
                    "architectures."
                ),
            )
            logger.info(
                f"HADRDiagramGenerator model initialised ({self.ai_model_name})"
            )
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
        service_diagram_descriptions: Optional[Dict[str, Dict[str, List[str]]]] = None,
    ) -> PatternDiagramBundle:
        """
        Generate diagrams for every DR-strategy × lifecycle-phase combination.

        Args:
            pattern_name:       Human-readable pattern title.
            services:           List of canonical service names in the pattern.
            hadr_text_sections: Output of HADRDocumentationGenerator — maps
                                DR strategy → generated Markdown text.
            pattern_context:    Pattern metadata (title, solution overview, etc.)
            service_diagram_descriptions:
                Optional dict of service_name → dr_strategy → [descriptions]
                extracted from ingested service-level HA/DR diagrams.  These
                are injected into the prompt as reference architecture context
                so the LLM can produce more accurate new diagrams.

        Returns:
            PatternDiagramBundle with up to 12 DiagramArtifact entries.
        """
        bundle = PatternDiagramBundle(pattern_name=pattern_name)

        for strategy in DR_STRATEGIES:
            strategy_text = hadr_text_sections.get(strategy, "")
            # Split the strategy text into per-phase sections
            phase_texts = self._split_phases(strategy_text)

            # Collect per-service diagram descriptions for this strategy
            strategy_diag_context = self._build_diagram_context(
                service_diagram_descriptions, strategy
            )

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
                    reference_diagram_descriptions=strategy_diag_context,
                )
                bundle.diagrams[(strategy, phase)] = artifact

        total = len(bundle.diagrams)
        fallbacks = sum(1 for a in bundle.all_artifacts() if a.is_fallback)
        logger.info(
            f"Generated {total} diagrams for '{pattern_name}' "
            f"({fallbacks} fallbacks)"
        )
        return bundle

    @staticmethod
    def _build_diagram_context(
        service_diagram_descriptions: Optional[Dict[str, Dict[str, List[str]]]],
        strategy: str,
    ) -> str:
        """
        Build a prompt-ready text block summarising the reference service-level
        HA/DR diagram descriptions for a single DR strategy.

        Returns an empty string if no descriptions are available.
        """
        if not service_diagram_descriptions:
            return ""
        lines: List[str] = []
        for svc_name, strategy_map in service_diagram_descriptions.items():
            descs = strategy_map.get(strategy, [])
            for d in descs:
                if d:
                    lines.append(f"  - {svc_name}: {d}")
        if not lines:
            return ""
        return (
            "# Reference Service-Level HA/DR Diagrams (from ingested docs)\n"
            "These describe the EXISTING architecture diagrams from the\n"
            "service-level HA/DR documentation. Use them as visual inspiration\n"
            "for the component layout, replication arrows, and state labels\n"
            "in the NEW diagram you are generating.\n"
            + "\n".join(lines)
        )

    # ─── Async public API ────────────────────────────────────────────────

    async def agenerate_all_diagrams(
        self,
        pattern_name: str,
        services: List[str],
        hadr_text_sections: Dict[str, str],
        pattern_context: Dict[str, Any],
        service_diagram_descriptions: Optional[Dict[str, Dict[str, List[str]]]] = None,
        timeout_per_diagram: float = 180.0,
        max_concurrent: int = 6,
    ) -> PatternDiagramBundle:
        """
        Async version of ``generate_all_diagrams`` — generates up to 12
        diagrams.

        **Programmatic mode** (``use_ai_diagrams=False``, the default):
        All 12 diagrams are built synchronously in < 1 second with zero
        Gemini calls.  The semaphore and timeout are not used.

        **AI mode** (``use_ai_diagrams=True``):
        SVG generation is parallelised via ``asyncio.gather`` with a
        ``Semaphore(max_concurrent)`` cap.  draw.io XML is still built
        programmatically (the AI draw.io call was the biggest token sink
        and added no value over the deterministic builder).

        Args:
            pattern_name:         Human-readable pattern title.
            services:             List of canonical service names.
            hadr_text_sections:   DR strategy → generated Markdown text.
            pattern_context:      Pattern metadata.
            service_diagram_descriptions:
                Optional dict of service_name → dr_strategy → [descriptions]
                from ingested service-level HA/DR diagrams.
            timeout_per_diagram:  Max seconds per single diagram when using
                                  AI (default 180, ignored in programmatic mode).
            max_concurrent:       Concurrency cap for AI mode (default 6).

        Returns:
            PatternDiagramBundle with up to 12 DiagramArtifact entries.
        """
        bundle = PatternDiagramBundle(pattern_name=pattern_name)

        # ── Fast path: programmatic (no AI) ──────────────────────────────
        if not self.use_ai_diagrams:
            import time
            t0 = time.monotonic()

            for strategy in DR_STRATEGIES:
                strategy_text = hadr_text_sections.get(strategy, "")
                phase_texts = self._split_phases(strategy_text)
                for phase in LIFECYCLE_PHASES:
                    phase_text = phase_texts.get(phase, "")
                    artifact = self._generate_single_diagram(
                        pattern_name, services, strategy,
                        phase, phase_text, pattern_context,
                    )
                    bundle.diagrams[(strategy, phase)] = artifact

            elapsed = time.monotonic() - t0
            logger.info(
                f"Programmatic generation of {len(bundle.diagrams)} diagrams "
                f"for '{pattern_name}' completed in {elapsed:.2f}s "
                f"(zero AI calls)"
            )
            return bundle

        # ── AI path: semaphore-gated parallel Gemini calls ───────────────
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _gen_one(
            strategy: str, phase: str, phase_text: str,
            diag_context: str = "",
        ):
            """Generate one diagram with concurrency limit and timeout."""
            async with semaphore:
                try:
                    coro = asyncio.to_thread(
                        self._generate_single_diagram,
                        pattern_name, services, strategy,
                        phase, phase_text, pattern_context,
                        diag_context,
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
                        svg_content=self._build_programmatic_svg(
                            strategy, phase, services
                        ),
                        drawio_xml=self._build_programmatic_drawio(
                            strategy, phase, services
                        ),
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
                        svg_content=self._build_programmatic_svg(
                            strategy, phase, services
                        ),
                        drawio_xml=self._build_programmatic_drawio(
                            strategy, phase, services
                        ),
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
            ref_diag_context = self._build_diagram_context(
                service_diagram_descriptions, strategy
            )
            for phase in LIFECYCLE_PHASES:
                phase_text = phase_texts.get(phase, "")
                logger.info(f"Scheduling async diagram: {strategy} / {phase}")
                tasks.append(_gen_one(strategy, phase, phase_text, ref_diag_context))

        # Execute all (up to max_concurrent at a time)
        results = await asyncio.gather(*tasks, return_exceptions=False)

        for strategy, phase, artifact in results:
            bundle.diagrams[(strategy, phase)] = artifact

        total = len(bundle.diagrams)
        fallbacks = sum(1 for a in bundle.all_artifacts() if a.is_fallback)
        logger.info(
            f"AI-generated {total} diagrams for '{pattern_name}' "
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
        reference_diagram_descriptions: str = "",
    ) -> DiagramArtifact:
        """Generate SVG + draw.io XML for one (strategy, phase) pair.

        When ``use_ai_diagrams`` is False (default), both SVG and draw.io
        are built programmatically — zero Gemini calls, deterministic
        output, always-valid XML.

        When ``use_ai_diagrams`` is True, SVG is generated via Gemini
        (with one retry on invalid output) while draw.io is still built
        programmatically (the AI draw.io call was the biggest token sink
        and added no value over the deterministic builder).
        """
        artifact = DiagramArtifact(
            dr_strategy=dr_strategy,
            lifecycle_phase=lifecycle_phase,
        )

        # ── draw.io is ALWAYS programmatic (biggest token/speed win) ─────
        artifact.drawio_xml = self._build_programmatic_drawio(
            dr_strategy, lifecycle_phase, services
        )

        if not self.use_ai_diagrams or not self.model:
            # ── Fully programmatic mode (default) ────────────────────────
            artifact.svg_content = self._build_programmatic_svg(
                dr_strategy, lifecycle_phase, services
            )
        else:
            # ── AI SVG mode (opt-in) ─────────────────────────────────────
            svg_content = self._generate_svg(
                pattern_name, services, dr_strategy,
                lifecycle_phase, phase_description, pattern_context,
            )
            valid_svg, svg_content = self._validate_and_fix_svg(svg_content)
            if not valid_svg:
                logger.warning(
                    f"SVG invalid for {dr_strategy}/{lifecycle_phase}, retrying…"
                )
                svg_content = self._generate_svg(
                    pattern_name, services, dr_strategy,
                    lifecycle_phase, phase_description, pattern_context,
                    retry_hint=(
                        "Previous SVG was malformed. Ensure valid XML "
                        "with xmlns and viewBox."
                    ),
                    reference_diagram_descriptions=reference_diagram_descriptions,
                )
                valid_svg, svg_content = self._validate_and_fix_svg(svg_content)
                if not valid_svg:
                    logger.error(
                        f"SVG retry failed for {dr_strategy}/{lifecycle_phase}"
                    )
                    svg_content = self._build_programmatic_svg(
                        dr_strategy, lifecycle_phase, services
                    )
                    artifact.is_fallback = True

            artifact.svg_content = svg_content

        # ── SVG → PNG conversion ─────────────────────────────────────────
        artifact.png_bytes = self._svg_to_png(artifact.svg_content)

        # ── Store description ────────────────────────────────────────────
        artifact.description = phase_description

        return artifact

    # ─── Programmatic diagram builders (zero AI calls) ───────────────────

    @staticmethod
    def _build_programmatic_svg(
        dr_strategy: str,
        lifecycle_phase: str,
        services: List[str],
    ) -> str:
        """
        Build an SVG component diagram entirely in Python — no Gemini calls.

        Layout: two regions side-by-side (Primary + DR), each service drawn
        as a colour-coded rounded rectangle with a state label, connected by
        dashed arrows.  A legend and title are included.

        The output is always valid SVG (no retry logic needed).
        """
        states = STATE_MATRIX.get(
            (dr_strategy, lifecycle_phase),
            RegionStates("Active", "Active", "Standby", "Standby", "Replication"),
        )

        n = len(services)
        svc_h = 55                          # vertical spacing per service
        region_top_pad = 80                 # space for region label
        region_h = region_top_pad + max(n, 1) * svc_h + 20
        canvas_h = max(600, region_h + 130) # room for title + legend

        parts: List[str] = []

        # ── Header ───────────────────────────────────────────────────────
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 900 {canvas_h}" width="900" height="{canvas_h}">'
        )
        parts.append(
            '<defs>'
            '<marker id="ah" markerWidth="10" markerHeight="7" '
            'refX="10" refY="3.5" orient="auto">'
            '<polygon points="0 0,10 3.5,0 7" fill="#555"/>'
            '</marker>'
            '</defs>'
        )
        parts.append(
            '<style>'
            'text{font-family:Arial,Helvetica,sans-serif}'
            '.t{font-size:17px;font-weight:bold;fill:#222}'
            '.rl{font-size:14px;font-weight:bold;fill:#333}'
            '.sn{font-size:12px;fill:#fff}'
            '.st{font-size:11px;font-style:italic}'
            '.al{font-size:10px;fill:#555}'
            '.lg{font-size:10px;fill:#555}'
            '</style>'
        )

        # Background
        parts.append(f'<rect width="900" height="{canvas_h}" fill="#FAFAFA" rx="4"/>')

        # Title
        title_text = f"{dr_strategy} \u2014 {lifecycle_phase}"
        parts.append(
            f'<text x="450" y="35" text-anchor="middle" class="t">'
            f'{title_text}</text>'
        )

        # ── Regions ──────────────────────────────────────────────────────
        parts.append(
            f'<rect x="30" y="55" width="390" height="{region_h}" '
            f'rx="10" fill="#E3F2FD" stroke="#1565C0" stroke-width="1.5"/>'
        )
        parts.append(
            '<text x="225" y="82" text-anchor="middle" class="rl">'
            'Primary Region</text>'
        )
        parts.append(
            f'<rect x="480" y="55" width="390" height="{region_h}" '
            f'rx="10" fill="#FFF3E0" stroke="#E65100" stroke-width="1.5"/>'
        )
        parts.append(
            '<text x="675" y="82" text-anchor="middle" class="rl">'
            'DR Region</text>'
        )

        # ── Service boxes + arrows ───────────────────────────────────────
        for i, svc in enumerate(services):
            is_core = _is_data_service(svc)
            p_state = states.primary_core if is_core else states.primary_non_core
            d_state = states.dr_core if is_core else states.dr_non_core
            p_color = STATE_COLORS.get(p_state, "#9E9E9E")
            d_color = STATE_COLORS.get(d_state, "#9E9E9E")

            y = 100 + i * svc_h

            # Primary box
            parts.append(
                f'<rect x="55" y="{y}" width="170" height="38" '
                f'rx="6" fill="{p_color}"/>'
            )
            parts.append(
                f'<text x="140" y="{y + 24}" text-anchor="middle" '
                f'class="sn">{svc}</text>'
            )
            parts.append(
                f'<text x="140" y="{y + 50}" text-anchor="middle" '
                f'class="st" fill="{p_color}">{p_state}</text>'
            )

            # DR box
            dr_opacity = ' opacity="0.5"' if d_state in ("Not-Deployed", "Scaled-Down") else ""
            parts.append(
                f'<rect x="505" y="{y}" width="170" height="38" '
                f'rx="6" fill="{d_color}"{dr_opacity}/>'
            )
            parts.append(
                f'<text x="590" y="{y + 24}" text-anchor="middle" '
                f'class="sn">{svc}</text>'
            )
            parts.append(
                f'<text x="590" y="{y + 50}" text-anchor="middle" '
                f'class="st" fill="{d_color}">{d_state}</text>'
            )

            # Dashed arrow
            parts.append(
                f'<line x1="225" y1="{y + 19}" x2="503" y2="{y + 19}" '
                f'stroke="#888" stroke-width="1" stroke-dasharray="4,3" '
                f'marker-end="url(#ah)"/>'
            )

        # Central arrow label
        if n > 0:
            mid_y = 100 + (n // 2) * svc_h + 10
            parts.append(
                f'<text x="364" y="{mid_y}" text-anchor="middle" '
                f'class="al">{states.arrow_label}</text>'
            )

        # ── Legend ────────────────────────────────────────────────────────
        legend_y = region_h + 75
        for j, (state_name, color) in enumerate(STATE_COLORS.items()):
            lx = 30 + j * 145
            parts.append(
                f'<rect x="{lx}" y="{legend_y}" width="12" height="12" '
                f'rx="2" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{lx + 16}" y="{legend_y + 11}" '
                f'class="lg">{state_name}</text>'
            )

        parts.append('</svg>')
        return "\n".join(parts)

    @staticmethod
    def _build_programmatic_drawio(
        dr_strategy: str,
        lifecycle_phase: str,
        services: List[str],
    ) -> str:
        """
        Build draw.io XML entirely in Python — no Gemini calls.

        Uses the ``DRAWIO_SERVICE_ICONS`` registry for official AWS/GCP
        icon shapes and the ``STATE_COLORS`` palette for state-dependent
        colouring.  The output is always valid mxfile XML.
        """
        states = STATE_MATRIX.get(
            (dr_strategy, lifecycle_phase),
            RegionStates("Active", "Active", "Standby", "Standby", "Replication"),
        )

        n = len(services)
        svc_spacing = 90
        region_h = 80 + max(n, 1) * svc_spacing + 30
        cells: List[str] = []
        cid = 10  # next cell ID counter

        for i, svc in enumerate(services):
            is_core = _is_data_service(svc)
            p_state = states.primary_core if is_core else states.primary_non_core
            d_state = states.dr_core if is_core else states.dr_non_core
            p_color = STATE_COLORS.get(p_state, "#9E9E9E")
            d_color = STATE_COLORS.get(d_state, "#9E9E9E")
            y = 100 + i * svc_spacing

            icon_style = get_drawio_icon_style(svc)

            # ── Primary service cell ─────────────────────────────────────
            if icon_style:
                p_style = (
                    f"{icon_style}whiteSpace=wrap;fillColor={p_color};"
                    f"fontColor=#232F3E;strokeColor={p_color};fontStyle=1;"
                    f"fontSize=11;labelPosition=center;"
                    f"verticalLabelPosition=bottom;verticalAlign=top;"
                    f"align=center;"
                )
                w, h = 60, 60
            else:
                p_style = (
                    f"rounded=1;whiteSpace=wrap;fillColor={p_color};"
                    f"fontColor=#ffffff;strokeColor=#757575;"
                    f"fontSize=11;fontStyle=1;"
                )
                w, h = 160, 45

            p_opacity = "opacity=50;" if p_state in ("Not-Deployed", "Scaled-Down") else ""
            cells.append(
                f'        <mxCell id="{cid}" '
                f'value="{svc}&#10;[{p_state}]" '
                f'style="{p_style}{p_opacity}" vertex="1" parent="1">\n'
                f'          <mxGeometry x="80" y="{y}" '
                f'width="{w}" height="{h}" as="geometry"/>\n'
                f'        </mxCell>'
            )
            p_id = cid
            cid += 1

            # Primary state badge
            cells.append(
                f'        <mxCell id="{cid}" value="{p_state}" '
                f'style="text;fontSize=10;fontStyle=2;'
                f'fontColor={p_color};align=center;" '
                f'vertex="1" parent="1">\n'
                f'          <mxGeometry x="65" y="{y + h + 2}" '
                f'width="90" height="18" as="geometry"/>\n'
                f'        </mxCell>'
            )
            cid += 1

            # ── DR service cell ──────────────────────────────────────────
            if icon_style:
                d_style = (
                    f"{icon_style}whiteSpace=wrap;fillColor={d_color};"
                    f"fontColor=#232F3E;strokeColor={d_color};fontStyle=1;"
                    f"fontSize=11;labelPosition=center;"
                    f"verticalLabelPosition=bottom;verticalAlign=top;"
                    f"align=center;"
                )
            else:
                d_style = (
                    f"rounded=1;whiteSpace=wrap;fillColor={d_color};"
                    f"fontColor=#ffffff;strokeColor=#757575;"
                    f"fontSize=11;fontStyle=1;"
                )

            d_opacity = "opacity=50;" if d_state in ("Not-Deployed", "Scaled-Down") else ""
            cells.append(
                f'        <mxCell id="{cid}" '
                f'value="{svc}&#10;[{d_state}]" '
                f'style="{d_style}{d_opacity}" vertex="1" parent="1">\n'
                f'          <mxGeometry x="500" y="{y}" '
                f'width="{w}" height="{h}" as="geometry"/>\n'
                f'        </mxCell>'
            )
            d_id = cid
            cid += 1

            # DR state badge
            cells.append(
                f'        <mxCell id="{cid}" value="{d_state}" '
                f'style="text;fontSize=10;fontStyle=2;'
                f'fontColor={d_color};align=center;" '
                f'vertex="1" parent="1">\n'
                f'          <mxGeometry x="485" y="{y + h + 2}" '
                f'width="90" height="18" as="geometry"/>\n'
                f'        </mxCell>'
            )
            cid += 1

            # ── Edge between primary ↔ DR ────────────────────────────────
            cells.append(
                f'        <mxCell id="{cid}" '
                f'value="{states.arrow_label}" '
                f'style="edgeStyle=orthogonalEdgeStyle;'
                f'strokeColor=#666666;fontSize=9;" '
                f'edge="1" source="{p_id}" target="{d_id}" parent="1">\n'
                f'          <mxGeometry relative="1" as="geometry"/>\n'
                f'        </mxCell>'
            )
            cid += 1

        cells_str = "\n".join(cells)
        esc_name = f"{dr_strategy} - {lifecycle_phase}"

        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<mxfile host="draw.io">\n'
            f'  <diagram name="{esc_name}" id="prog1">\n'
            '    <mxGraphModel dx="1200" dy="800" grid="1" '
            'gridSize="10" guides="1">\n'
            '      <root>\n'
            '        <mxCell id="0"/>\n'
            '        <mxCell id="1" parent="0"/>\n'
            '        <mxCell id="2" value="Primary Region" '
            'style="rounded=1;whiteSpace=wrap;fillColor=#dae8fc;'
            'strokeColor=#6c8ebf;fontSize=14;fontStyle=1;'
            'verticalAlign=top;" vertex="1" parent="1">\n'
            f'          <mxGeometry x="30" y="50" width="350" '
            f'height="{region_h}" as="geometry"/>\n'
            '        </mxCell>\n'
            '        <mxCell id="3" value="DR Region" '
            'style="rounded=1;whiteSpace=wrap;fillColor=#fff2cc;'
            'strokeColor=#d6b656;fontSize=14;fontStyle=1;'
            'verticalAlign=top;" vertex="1" parent="1">\n'
            f'          <mxGeometry x="420" y="50" width="350" '
            f'height="{region_h}" as="geometry"/>\n'
            '        </mxCell>\n'
            f'{cells_str}\n'
            '      </root>\n'
            '    </mxGraphModel>\n'
            '  </diagram>\n'
            '</mxfile>'
        )

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
        reference_diagram_descriptions: str = "",
    ) -> str:
        """Ask Gemini to produce an SVG component diagram."""
        services_list = "\n".join(f"  - {s}" for s in services)
        state_guide = self._state_guide(dr_strategy, lifecycle_phase)

        ref_diag_section = ""
        if reference_diagram_descriptions:
            ref_diag_section = f"""
{reference_diagram_descriptions}

Use the above reference diagram descriptions to guide your layout: which
services appear in which region, how replication arrows flow, and which
components are active vs. standby.  The NEW diagram should reflect the new
pattern's services but follow the same architectural patterns shown in the
references.
"""

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
{ref_diag_section}
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
                    max_output_tokens=4096,
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
        reference_diagram_descriptions: str = "",
    ) -> str:
        """Ask Gemini to produce draw.io-compatible XML."""
        services_list = "\n".join(f"  - {s}" for s in services)
        state_guide = self._state_guide(dr_strategy, lifecycle_phase)

        ref_diag_section = ""
        if reference_diagram_descriptions:
            ref_diag_section = f"""
{reference_diagram_descriptions}

Use the above reference diagram descriptions to guide your layout: which
services appear in which region, how replication arrows flow, and which
components are active vs. standby.
"""

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
{ref_diag_section}
# Colour Palette for Service States
{json.dumps(STATE_COLORS, indent=2)}

# Service Icon Shape Registry (draw.io built-in AWS 4.0 + GCP shape libraries)
{json.dumps(DRAWIO_SERVICE_ICONS, indent=2)}

# Layout Rules
1. Two container shapes side-by-side: "Primary Region" (fillColor=#dae8fc)
   and "DR Region" (fillColor=#fff2cc).
2. Inside each container, add a cell for EVERY service in the pattern.
3. **Use the official cloud-provider icon shape** from the registry above
   for each service. Set the cell style to include the `shape=...;resIcon=...`
   fragment from the registry. If a service is not in the registry, fall back
   to a plain `rounded=1;whiteSpace=wrap;` rectangle.
4. Set each icon cell size to width="60" height="60" so the icon renders.
   Place the service name as a label below the icon using
   `labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;`.
5. Tint the icon's `fillColor` using the state colour from the palette.
   For "Not-Deployed" or "Scaled-Down" states, also add `opacity=50;`.
6. Add a small text cell below each icon showing the state label
   (e.g., "Active", "Standby") in the matching state colour,
   styled as `text;fontSize=10;fontStyle=2;` (italic).
7. Include the service name and state in the cell value, e.g.
   "Amazon RDS&#10;[Active]" (use &#10; for newline).
8. Add edge cells between Primary ↔ DR service pairs showing the
   replication/failover mechanism as a label.
9. Set the diagram name to "{dr_strategy} - {lifecycle_phase}".

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
                    max_output_tokens=4096,
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
        """Generate a minimal placeholder draw.io XML with cloud-provider icons."""
        cells = []
        cell_id = 10
        y_pos = 100

        for svc in services[:8]:
            icon_style = get_drawio_icon_style(svc)
            if icon_style:
                # Use the official icon shape with grey tint for unknown state
                style = (
                    f"{icon_style}whiteSpace=wrap;fillColor=#BDBDBD;"
                    f"fontColor=#232F3E;strokeColor=#757575;fontStyle=1;"
                    f"fontSize=11;labelPosition=center;"
                    f"verticalLabelPosition=bottom;verticalAlign=top;"
                    f"align=center;opacity=50;"
                )
                width, height = 60, 60
            else:
                # Plain rectangle fallback for unrecognised services
                style = (
                    "rounded=1;whiteSpace=wrap;fillColor=#BDBDBD;"
                    "fontColor=#ffffff;strokeColor=#757575;"
                )
                width, height = 160, 45
            cells.append(
                f'        <mxCell id="{cell_id}" value="{svc}&#10;[Unknown]" '
                f'style="{style}" vertex="1" parent="1">\n'
                f'          <mxGeometry x="60" y="{y_pos}" width="{width}" height="{height}" as="geometry"/>\n'
                f'        </mxCell>'
            )
            cell_id += 1
            y_pos += 80 if icon_style else 60

        cells_str = "\n".join(cells)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="draw.io">
  <diagram name="{dr_strategy} - {lifecycle_phase}" id="fallback">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Primary Region" style="rounded=1;whiteSpace=wrap;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="30" y="50" width="350" height="{y_pos + 30}" as="geometry"/>
        </mxCell>
{cells_str}
        <mxCell id="100" value="DR Region" style="rounded=1;whiteSpace=wrap;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=14;fontStyle=1;verticalAlign=top;" vertex="1" parent="1">
          <mxGeometry x="420" y="50" width="350" height="{y_pos + 30}" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""
