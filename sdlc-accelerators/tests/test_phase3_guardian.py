"""Phase 3: Governance Guardian extracts 9 sections; assessment boundary enforced."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from assessment.engine import assess_sections, classify_finding
from extraction.sections import completeness, extract_sections


def test_extracts_all_nine_sections():
    md = (ROOT / "examples/fnol/outputs/app-blueprint.md").read_text()
    secs = extract_sections(md)
    assert sorted(secs.keys()) == list(range(1, 10))
    assert completeness(secs) == []


def test_critical_is_showstopper():
    assert classify_finding("critical") == "showstopper"
    assert classify_finding("medium") == "tech_debt"


def test_assessment_rubric_boundary_enforced():
    import pytest
    with pytest.raises(NotImplementedError):
        assess_sections({})
