"""/accelerator.generate — governance gate + deterministic generation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..generator.engine import generate


def _hash(path: str) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_generate(blueprint_json: str, out_dir: str, template_root: str,
                 tech_debt_signal: str = "resume") -> dict:
    """1. governance gate (recordTechDebt signal), 2. generate.
    Showstoppers (signal='stop') block generation. Tech debt resumes.
    """
    if tech_debt_signal == "stop":
        return {"blocked": True, "reason": "showstopper findings present — fix and re-assess"}
    result = generate(blueprint_json, out_dir, template_root)
    result["blueprint_hash"] = _hash(blueprint_json)
    result["blocked"] = False
    return result
