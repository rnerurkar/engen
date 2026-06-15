"""Catalog ingestion CLI (platform-team maintenance job — NOT a runtime MCP tool).

  python -m catalog_ingestion.cli patterns      # PDFs -> Vertex AI Search Pattern Catalog
  python -m catalog_ingestion.cli skills         # GitHub repo -> Vertex AI Search Skill Catalog
  python -m catalog_ingestion.cli agent-cards    # local JSON -> Apigee API Hub (a2a_agent)
  python -m catalog_ingestion.cli all
"""
from __future__ import annotations

import argparse
import sys

from . import ingest_patterns, ingest_skills, register_agent_cards


def main(argv=None):
    ap = argparse.ArgumentParser(description="SDLC Accelerators catalog ingestion")
    ap.add_argument("target", choices=["patterns", "skills", "agent-cards", "all"])
    ap.add_argument("--config", default=None, help="path to ingestion-config.yaml")
    args = ap.parse_args(argv)

    runners = {
        "patterns": ingest_patterns.run,
        "skills": ingest_skills.run,
        "agent-cards": register_agent_cards.run,
    }
    targets = list(runners) if args.target == "all" else [args.target]
    for t in targets:
        print(f"==> {t}")
        result = runners[t](args.config)
        print(f"    {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
