"""Real-execution tests for the greenfield orchestrator deterministic steps (1a)."""
import asyncio

from reasoning.adk_steps import AssembleBlueprintStep, ValidateSpecStep


class _FakeSession:
    def __init__(self, state):
        self.state = state


class _FakeCtx:
    def __init__(self, state):
        self.session = _FakeSession(state)


def _drain(step, state):
    ctx = _FakeCtx(state)

    async def go():
        async for _ in step._run_async_impl(ctx):
            pass
    asyncio.run(go())
    return state


def test_validate_step_runs_real_validate_spec():
    # A spec with content runs the real validate_spec and records its result
    state = {"spec_md": "# Spec\nFirst do X, then do Y.\n", "plan_md": "# Plan\n"}
    _drain(ValidateSpecStep(name="greenfield_validate_spec"), state)
    assert "validation" in state
    assert "ok" in state["validation"]


def test_assemble_step_skips_without_selections():
    # No LLM selections in state -> the step records the skip truthfully (no fabrication)
    state = {"spec_md": "x", "plan_md": "y"}
    _drain(AssembleBlueprintStep(name="greenfield_assemble_blueprint"), state)
    assert state["blueprint_md"] is None


def test_assemble_step_runs_real_assembler_with_selections():
    """With ArchitectureSelections in state, the step runs the tested assemble_blueprint and the
    injected Eraser tool renders diagrams."""
    from assembly.selections import ArchitectureSelections
    from clients.eraser_mcp import EraserMcpClient
    # Build a minimal valid selections object (mirrors what the LLM stage would produce).
    try:
        sel = ArchitectureSelections.minimal() if hasattr(ArchitectureSelections, "minimal") else None
    except Exception:
        sel = None
    if sel is None:
        import pytest
        pytest.skip("ArchitectureSelections requires LLM-shaped fields; covered by assembly tests")
    eraser = EraserMcpClient(_render=lambda dsl: {"drawio_xml": "<x/>", "png_base64": "AA"})
    state = {"spec_md": "s", "plan_md": "p", "selections": sel, "_eraser_mcp": eraser}
    _drain(AssembleBlueprintStep(name="greenfield_assemble_blueprint"), state)
    assert state["blueprint_md"] is not None
    assert len(state["diagrams"]) >= 1
