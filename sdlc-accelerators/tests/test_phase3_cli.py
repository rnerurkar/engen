"""Phase 3: CLI generates FNOL deterministically; governance gate blocks showstoppers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.commands.generate import run_generate

BP = str(ROOT / "examples/fnol/outputs/app-blueprint.json")
TPL = str(ROOT / "templates/code")


def test_cli_generates_fnol(tmp_path):
    r = run_generate(BP, str(tmp_path / "out"), TPL)
    assert r["blocked"] is False
    assert r["count"] == 15


def test_generation_is_byte_identical(tmp_path):
    run_generate(BP, str(tmp_path / "a"), TPL)
    run_generate(BP, str(tmp_path / "b"), TPL)
    a = sorted((tmp_path / "a").rglob("*.py"))
    b = sorted((tmp_path / "b").rglob("*.py"))
    assert [p.read_text() for p in a] == [q.read_text() for q in b]


def test_governance_gate_blocks_showstopper(tmp_path):
    r = run_generate(BP, str(tmp_path / "out"), TPL, tech_debt_signal="stop")
    assert r["blocked"] is True


def test_generated_code_compiles(tmp_path):
    import py_compile
    run_generate(BP, str(tmp_path / "out"), TPL)
    for f in (tmp_path / "out").rglob("*.py"):
        py_compile.compile(str(f), doraise=True)
