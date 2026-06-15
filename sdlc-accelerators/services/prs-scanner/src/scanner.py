"""PRS Scanner — Production Readiness Scan.

Enforces the constitution rules against generated code BEFORE the PR can merge.
Each check maps to a numbered constitution rule. Returns findings; any CRITICAL
finding fails the scan (the Harness pipeline gates on exit code).

This is the enforcement backbone that makes "compliant by construction" real:
without it, the 20 constitution rules are advisory.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CRITICAL = "critical"
HIGH = "high"


@dataclass
class Finding:
    rule: str          # e.g. "Rule 5"
    severity: str
    file: str
    message: str


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == CRITICAL for f in self.findings)

    def exit_code(self) -> int:
        return 0 if self.passed else 1


# ---- Secret detection (Rule 5) ----
_SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "Google API key"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-style secret key"),
    (re.compile(r"sk_live_[A-Za-z0-9]+"), "Stripe live key"),
    (re.compile(r"password\s*=\s*['\"][^'\"]+['\"]"), "hardcoded password"),
    (re.compile(r"postgresql://[^:]+:[^@]+@"), "DB connection string with credentials"),
]


def scan_secrets(py_files: list[Path]) -> list[Finding]:
    """Rule 5: never hardcode secrets."""
    out = []
    for f in py_files:
        text = f.read_text()
        for pat, label in _SECRET_PATTERNS:
            if pat.search(text):
                out.append(Finding("Rule 5", CRITICAL, f.name, f"Hardcoded secret detected ({label})"))
    return out


def scan_no_print(py_files: list[Path]) -> list[Finding]:
    """Rule 15: structured logging, never print() in agent code."""
    out = []
    for f in py_files:
        if "test" in f.name:
            continue
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            out.append(Finding("Rule 18", CRITICAL, f.name, "Generated file does not parse"))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                out.append(Finding("Rule 15", HIGH, f.name, "print() in agent code — use structured logging"))
    return out


def scan_model_armor(agent_dir: Path, blueprint: dict) -> list[Finding]:
    """Rule 7: every screened agent must register Model Armor callbacks."""
    out = []
    sc = blueprint.get("screening_config", {})
    inp = set(sc.get("agents_with_input_screening", []))
    outp = set(sc.get("agents_with_output_screening", []))
    for agent in inp | outp:
        f = agent_dir / f"{agent}.py"
        if not f.exists():
            out.append(Finding("Rule 7", CRITICAL, f"{agent}.py", "Screened agent file missing"))
            continue
        text = f.read_text()
        if agent in inp and "screen_input" not in text:
            out.append(Finding("Rule 7", CRITICAL, f.name, f"{agent} missing input Model Armor screening"))
        if agent in outp and "screen_output" not in text:
            out.append(Finding("Rule 7", CRITICAL, f.name, f"{agent} missing output Model Armor screening"))
    return out


def scan_no_raw_terraform(tf_files: list[Path]) -> list[Finding]:
    """Rule 4: company modules only — no raw google_*/aws_* resources."""
    out = []
    raw = re.compile(r'resource\s+"(google|aws)_')
    for f in tf_files:
        if raw.search(f.read_text()):
            out.append(Finding("Rule 4", CRITICAL, f.name, "Raw google_*/aws_* resource — use company modules"))
    return out


def scan_no_deploy_commands(all_files: list[Path]) -> list[Finding]:
    """Rule 1: never deploy directly. Catches both shell strings and subprocess lists."""
    out = []
    deploy = re.compile(r"(terraform\s+apply|kubectl\s+apply|docker\s+push|gcloud\s+(run\s+deploy|deploy))")
    deploy_tokens = {"terraform", "kubectl", "docker", "gcloud"}
    deploy_actions = {"apply", "push", "deploy"}
    for f in all_files:
        if f.suffix in (".sh", ".yaml", ".yml"):
            if deploy.search(f.read_text()):
                out.append(Finding("Rule 1", CRITICAL, f.name,
                                    "Direct deploy command — goes through Jenkins/Harness"))
        elif f.suffix == ".py":
            text = f.read_text()
            if deploy.search(text):
                out.append(Finding("Rule 1", CRITICAL, f.name,
                                    "Direct deploy command — goes through Jenkins/Harness"))
                continue
            # Catch subprocess.run(["terraform", "apply"]) — a list of string literals
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.List):
                    strs = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                    if any(t in deploy_tokens for t in strs) and any(a in deploy_actions for a in strs):
                        out.append(Finding("Rule 1", CRITICAL, f.name,
                                            "Direct deploy (subprocess list) — use Jenkins/Harness"))
                        break
    return out


def scan_required_files(root: Path) -> list[Finding]:
    """Rules 11-13, 16: required artifacts must exist."""
    out = []
    required = {
        ".pre-commit-config.yaml": "Rule 11",
        "eval/golden-dataset.json": "Rule 12",
        "app/health.py": "Rule 13",
        "config/dynatrace/dashboard.json": "Rule 16",
    }
    for rel, rule in required.items():
        if not (root / rel).exists():
            out.append(Finding(rule, HIGH, rel, f"Required artifact missing ({rule})"))
    return out


def scan(generated_root: str, blueprint_path: str) -> ScanResult:
    """Run all checks against a generated project."""
    root = Path(generated_root)
    blueprint = json.loads(Path(blueprint_path).read_text())
    py_files = list(root.rglob("*.py"))
    tf_files = list(root.rglob("*.tf"))
    all_files = list(root.rglob("*"))
    agent_dir = root / "agents"

    result = ScanResult()
    result.findings += scan_secrets(py_files)
    result.findings += scan_no_print(py_files)
    if agent_dir.exists():
        result.findings += scan_model_armor(agent_dir, blueprint)
    result.findings += scan_no_raw_terraform(tf_files)
    result.findings += scan_no_deploy_commands([f for f in all_files if f.is_file()])
    result.findings += scan_required_files(root)
    return result
