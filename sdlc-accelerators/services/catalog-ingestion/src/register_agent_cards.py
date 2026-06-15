"""Register third-party agent cards in Apigee API Hub as type=a2a_agent.

ARCHITECTURE NOTE: agent discovery is via Apigee API Hub (the single discovery surface
for MCP servers + A2A agents + REST APIs), NOT Vertex AI Search. discover_integrations()
queries API Hub at reasoning time. This job registers each agent card so it becomes
discoverable. Agent cards are NOT embedded into a Vertex AI Search data store.

The card parsing + registration-payload building is real and tested; the API Hub API
call is wired through a client (TODO live).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import IngestionConfig

logger = logging.getLogger("catalog-ingestion.agent-cards")


@dataclass
class ApiHubRegistration:
    """The payload registered in Apigee API Hub for one A2A agent."""
    api_id: str
    display_name: str
    api_type: str = "a2a_agent"
    capabilities: list[str] = field(default_factory=list)
    agent_card_url: str = ""
    auth_method: str = ""
    lifecycle: str = "active"
    version: str = ""


def discover_agent_cards(source_dir: str) -> list[Path]:
    root = Path(source_dir)
    if not root.exists():
        raise FileNotFoundError(f"Agent-card source dir not found: {source_dir}")
    return sorted(root.rglob("*.json"))


def parse_agent_card(card_path: Path) -> dict:
    """Load an A2A Agent Card JSON (per the A2A agent-card schema)."""
    return json.loads(card_path.read_text())


def to_registration(card: dict, default_lifecycle: str = "active") -> ApiHubRegistration:
    """Map an A2A Agent Card to an API Hub registration payload.
    Supports the common agent-card shape: name, description, url, capabilities/skills, auth."""
    name = card.get("name") or card.get("agent", {}).get("name", "unknown-agent")
    # capabilities may be under 'capabilities', 'skills', or a2a 'skills[].id'
    caps = card.get("capabilities") or []
    if not caps and isinstance(card.get("skills"), list):
        caps = [s.get("id") or s.get("name") for s in card["skills"] if isinstance(s, dict)]
    auth = ""
    sec = card.get("securitySchemes") or card.get("authentication") or {}
    if isinstance(sec, dict) and sec:
        auth = next(iter(sec.keys()))
    elif isinstance(sec, str):
        auth = sec
    api_id = "a2a-" + str(name).lower().replace(" ", "-").replace("_", "-")
    return ApiHubRegistration(
        api_id=api_id,
        display_name=str(name),
        capabilities=[c for c in caps if c],
        agent_card_url=card.get("url") or card.get("agent_card_url", ""),
        auth_method=auth,
        lifecycle=card.get("lifecycle", default_lifecycle),
        version=str(card.get("version", "")),
    )


def register_in_api_hub(reg: ApiHubRegistration, project_id: str, location: str, instance: str) -> None:
    """Register one agent in Apigee API Hub.
    TODO(live): google.cloud.apihub_v1 ApiHubClient.create_api (+ versions/deployments)."""
    raise NotImplementedError(
        f"Wire Apigee API Hub create_api for '{reg.api_id}' "
        f"(type={reg.api_type}, {len(reg.capabilities)} capabilities) in {instance}."
    )


def run(config_path: str | None = None) -> dict:
    """Entry point: register all agent cards in Apigee API Hub."""
    cfg = IngestionConfig.load(config_path)
    ac = cfg.raw["agent_cards"]
    cards = discover_agent_cards(ac["source_dir"])
    regs = [to_registration(parse_agent_card(p), ac["api_hub"]["default_lifecycle"]) for p in cards]
    logger.info("agent_cards_discovered", extra={"count": len(cards)})

    for reg in regs:
        register_in_api_hub(reg, cfg.project_id, ac["api_hub"]["location"], ac["api_hub"]["api_hub_instance"])
    return {"discovered": len(cards), "registered": len(regs)}
