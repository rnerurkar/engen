"""Generation engine. Reads app-blueprint.json, applies the domain skill's
Jinja2 templates, writes the project. Deterministic: same json + templates ->
byte-identical output. This is the core of /accelerator.generate.
"""
from __future__ import annotations

import json
from pathlib import Path

# Reuse the validated agentic-ai-adk renderer.
from .adk_renderer import main as render_adk

ARCHETYPE_RENDERERS = {
    "agentic": render_adk,
    "agentic-ai": render_adk,
}


def generate(blueprint_path: str, out_dir: str, template_root: str) -> dict:
    """Generate code from app-blueprint.json for its archetype."""
    bp = json.loads(Path(blueprint_path).read_text())
    archetype = bp.get("metadata", {}).get("archetype", "agentic")
    renderer = ARCHETYPE_RENDERERS.get(archetype)
    if renderer is None:
        raise ValueError(f"No domain skill renderer for archetype '{archetype}'. "
                         f"Author one in skills/domain-skills/ and register it here.")
    tdir = str(Path(template_root) / 'agentic-ai-adk')
    renderer(blueprint_path, out_dir, template_dir=tdir)
    files = sorted(str(p.relative_to(out_dir)) for p in Path(out_dir).rglob("*.py"))
    return {"archetype": archetype, "files": files, "count": len(files)}
