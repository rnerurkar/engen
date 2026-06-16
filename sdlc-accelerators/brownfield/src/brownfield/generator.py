"""Brownfield migration code generator — picks the right template per integration from the
design contract and renders it with rollback + coexistence telemetry.

cutover strategy -> template:
  strangler-fig  -> strangler_proxy
  dual-publish   -> dual_write
  blue-green / hard-cutover / big-bang -> cutover_gate
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

STRATEGY_TEMPLATE = {
    "strangler-fig": "strangler_proxy.py.j2",
    "dual-publish": "dual_write.py.j2",
    "blue-green": "cutover_gate.py.j2",
    "hard-cutover": "cutover_gate.py.j2",
    "big-bang": "cutover_gate.py.j2",
}


def generate_migration_code(design_contract: dict, plan_decisions: list, spec,
                            template_dir: str, out_dir: str) -> dict:
    """Render one migration artifact per integration. Returns {files: [...], count: n}."""
    env = Environment(loader=FileSystemLoader(template_dir), keep_trailing_newline=True)
    plan_by_id = {d.integration_id: d for d in plan_decisions}
    name_by_id = {it.integration_id: it.name for it in spec.integrations}
    out = Path(out_dir)
    (out / "migrations").mkdir(parents=True, exist_ok=True)

    files = []
    for sub in design_contract["tech_substitutions"]:
        iid = sub["integration_id"]
        d = plan_by_id.get(iid)
        strategy = (d.cutover_strategy if d else "").lower()
        tmpl_name = STRATEGY_TEMPLATE.get(strategy, "cutover_gate.py.j2")
        tmpl = env.get_template(tmpl_name)
        rendered = tmpl.render(
            integration_id=iid, name=name_by_id.get(iid, iid),
            source="+".join(sub.get("source_tokens", [])),
            target="+".join(sub.get("target_tokens", [])),
            coexistence_window=(d.coexistence_window if d else ""),
            rollback_path=(d.rollback_path if d else "UNSPECIFIED"),
        )
        fname = f"migrations/{iid.lower().replace('-', '_')}_migration.py"
        (out / fname).write_text(rendered)
        files.append(fname)
    return {"files": sorted(files), "count": len(files)}


def check_rollback_paths(out_dir: str) -> list:
    """Brownfield PRS rule: every migration artifact must contain a rollback path.
    Returns a list of files missing 'def rollback' (constitution violation)."""
    violations = []
    for f in Path(out_dir).rglob("*_migration.py"):
        if "def rollback" not in f.read_text():
            violations.append(str(f))
    return violations
