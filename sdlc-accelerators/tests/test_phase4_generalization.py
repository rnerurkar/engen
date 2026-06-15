"""Phase 4 generalization: the SAME templates generate a DIFFERENT agentic use case.

Proves the renderer is schema-driven, not FNOL-shaped. The contract-review case
deliberately exercises dimensions FNOL lacks: LoopAgent at root, two A2A agents,
function tools alongside A2A in the same tools[] list, strict screening.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/accelerator-cli"))

from src.commands.generate import run_generate

TPL = str(ROOT / "templates/code")
FNOL = str(ROOT / "examples/fnol/outputs/app-blueprint.json")
CONTRACT = str(ROOT / "examples/contract-review/outputs/app-blueprint.json")


def _no_accidental_subtraction(out_dir: Path):
    """Hyphenated tool names must NOT render as `a - b - c` subtraction expressions.
    py_compile misses this; AST inspection catches it. Scoped to files that interpolate
    tool/agent names (agents, tools, main) — fixed-template files like the eval harness,
    which contain legitimate arithmetic, are excluded."""
    NAME_INTERPOLATED = ("agents", "tools", "callbacks")
    for f in out_dir.rglob("*.py"):
        rel = f.relative_to(out_dir)
        is_name_file = rel.parts[0] in NAME_INTERPOLATED or rel.name == "main.py"
        if not is_name_file:
            continue  # eval_inner_loop.py etc. are fixed templates, not name-interpolated
        tree = ast.parse(f.read_text())
        subs = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub)]
        assert not subs, f"{f.name} has subtraction (hyphen-name bug): {ast.dump(subs[0])}"


def test_contract_review_validates_same_schema():
    import json

    import jsonschema
    schema = json.loads((ROOT / "schemas/app-blueprint.schema.json").read_text())
    bp = json.loads(Path(CONTRACT).read_text())
    jsonschema.validate(bp, schema)


def test_contract_review_generates_correctly(tmp_path):
    out = tmp_path / "contract"
    r = run_generate(CONTRACT, str(out), TPL)
    assert r["blocked"] is False
    # All generated files parse AND contain no hyphen-subtraction bugs
    import py_compile
    for f in out.rglob("*.py"):
        py_compile.compile(str(f), doraise=True)
    _no_accidental_subtraction(out)


def test_loopagent_root_wraps_children(tmp_path):
    """The LoopAgent root must wrap its real child, not collapse to an empty LlmAgent."""
    out = tmp_path / "contract"
    run_generate(CONTRACT, str(out), TPL)
    root = (out / "agents" / "contract_review_loop.py").read_text()
    assert "build_review_chain()" in root
    assert "LlmAgent" not in root  # root LoopAgent node must not become an LlmAgent


def test_a2a_tools_use_a2a_accessor(tmp_path):
    """A2A tools must render get_a2a_agent(...), never a bare hyphenated identifier."""
    out = tmp_path / "contract"
    run_generate(CONTRACT, str(out), TPL)
    legal = (out / "agents" / "legal_risk.py").read_text()
    assert 'get_a2a_agent("legal-review-a2a")' in legal


def test_fnol_still_correct_after_fixes(tmp_path):
    """Regression: FNOL must still generate, and its A2A tool is now fixed too."""
    out = tmp_path / "fnol"
    r = run_generate(FNOL, str(out), TPL)
    assert r["count"] == 15
    _no_accidental_subtraction(out)
    sev = (out / "agents" / "severity_classifier.py").read_text()
    assert 'get_a2a_agent("body-shop-a2a")' in sev
