"""Phase 5: Terraform generation, PRS scanner, EvalOps, Harness pipeline."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.commands.generate import run_generate  # accelerator-cli

FNOL = str(ROOT / "examples/fnol/outputs/app-blueprint.json")
TPL = str(ROOT / "templates/code")


def _load(mod_name, rel_path):
    """Load a module by file path to avoid src.* package collisions across services."""
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod  # register so dataclass type resolution works
    spec.loader.exec_module(mod)
    return mod


_scanner = _load("prs_scanner_mod", "services/prs-scanner/src/scanner.py")
_golden = _load("golden_mod", "services/evalops/src/golden_dataset.py")
_evalrun = _load("evalrun_mod", "services/evalops/src/eval_runner.py")


# ---- #1 Terraform generation ----
def test_generate_emits_terraform(tmp_path):
    out = tmp_path / "out"
    run_generate(FNOL, str(out), TPL)
    assert (out / "terraform" / "main.tf").exists()
    assert (out / "terraform" / "agents.tf").exists()


def test_terraform_uses_company_modules_only(tmp_path):
    out = tmp_path / "out"
    run_generate(FNOL, str(out), TPL)
    main_tf = (out / "terraform" / "main.tf").read_text()
    assert 'resource "google_' not in main_tf
    assert 'resource "aws_' not in main_tf
    assert 'module "' in main_tf


def test_orchestrator_sa_is_delegation_only(tmp_path):
    out = tmp_path / "out"
    run_generate(FNOL, str(out), TPL)
    agents_tf = (out / "terraform" / "agents.tf").read_text()
    assert "sa_fnol_coordinator" in agents_tf
    assert "delegation only" in agents_tf


# ---- #2 PRS scanner ----
def test_prs_passes_clean_generated_code(tmp_path):
    out = tmp_path / "out"
    run_generate(FNOL, str(out), TPL)
    result = _scanner.scan(str(out), FNOL)
    crit = [f for f in result.findings if f.severity == "critical"]
    assert crit == [], f"unexpected critical findings: {[f.message for f in crit]}"
    assert result.passed


def test_prs_catches_violations(tmp_path):
    bad = tmp_path / "bad"
    (bad / "agents").mkdir(parents=True)
    (bad / "terraform").mkdir(parents=True)
    (bad / "agents" / "extract_details.py").write_text(
        'STRIPE_KEY = "sk_live_abc123def456"\n'
        'import subprocess\n'
        'subprocess.run(["terraform", "apply"])\n'
    )
    (bad / "terraform" / "main.tf").write_text('resource "google_cloud_run_service" "x" {}\n')
    result = _scanner.scan(str(bad), FNOL)
    caught = {f.rule for f in result.findings if f.severity == "critical"}
    assert {"Rule 1", "Rule 4", "Rule 5", "Rule 7"}.issubset(caught)
    assert not result.passed
    assert result.exit_code() == 1


# ---- #3 EvalOps ----
def test_golden_dataset_covers_all_agents(tmp_path):
    d = _golden.generate_seed(FNOL, str(tmp_path / "golden.json"))
    assert len(d["coverage"]["agents"]) == 8
    assert d["threshold"] == 0.90


def test_eval_gate_logic():
    assert _evalrun.gate(_evalrun.EvalResult(0.95, 0.90, True, {}, 10)) == 0
    assert _evalrun.gate(_evalrun.EvalResult(0.80, 0.90, False, {}, 10)) == 1


# ---- #4 Harness pipeline ----
def test_harness_pipeline_has_all_gates():
    pipe = (ROOT / ".harness" / "pipeline.yaml").read_text()
    for stage in ["Production Readiness Scan", "EvalOps Phase 1 Gate", "Sign & Attest",
                  "Provision Infrastructure", "Deploy to AgentEngine"]:
        assert stage in pipe
    assert "cosign" in pipe
    assert "Binary Authorization" in pipe
