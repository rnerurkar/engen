"""Load ingestion config from YAML. All env-specific values external to code.
The GitHub skills repo URL is configurable here (skills.github_repo_url)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngestionConfig:
    raw: dict

    @classmethod
    def load(cls, path: str | None = None) -> IngestionConfig:
        import yaml
        p = path or os.environ.get(
            "INGESTION_CONFIG",
            str(Path(__file__).resolve().parents[1] / "config" / "ingestion-config.yaml"),
        )
        with open(p) as f:
            return cls(raw=yaml.safe_load(f))

    @property
    def project_id(self) -> str:
        return self.raw["project_id"]

    @property
    def location(self) -> str:
        return self.raw.get("location", "global")

    @property
    def skills_repo_url(self) -> str:
        """Configurable GitHub skills repo URL."""
        return self.raw["skills"]["github_repo_url"]

    @property
    def skills_ref(self) -> str:
        return self.raw["skills"].get("github_ref", "main")

    def store(self, name: str) -> dict:
        return self.raw["vertex_ai_search"][name]
