"""Live LLM provider wiring: availability gating + the live invoke path (mocked SDK client)."""
import json
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from reasoning import llm_provider


def test_available_false_without_credentials(monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ok, reason = llm_provider.available()
    assert ok is False
    assert "credentials" in reason.lower()


def test_available_true_with_vertex_project(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-proj")
    ok, reason = llm_provider.available()
    assert ok is True


def test_invoke_calls_gemini_and_parses_json(monkeypatch):
    """The wired live path: build client, request JSON, parse the response into a dict."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    captured = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["system_instruction"] = config.system_instruction
            captured["mime"] = config.response_mime_type
            return types.SimpleNamespace(text=json.dumps({"selected_pattern": "SequentialAgent"}))

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(llm_provider, "_build_client", lambda: FakeClient())
    out = llm_provider.invoke("AUTHORED PROMPT", "spec+plan here")
    assert out == {"selected_pattern": "SequentialAgent"}
    assert captured["system_instruction"] == "AUTHORED PROMPT"   # prompt bound verbatim
    assert captured["mime"] == "application/json"                # JSON output requested


def test_harness_uses_live_provider_when_configured(monkeypatch):
    """invoke_llm_agent (no model_fn) routes to the live provider when available."""
    from reasoning.llm_harness import invoke_llm_agent
    monkeypatch.setattr(llm_provider, "available", lambda: (True, ""))
    monkeypatch.setattr(llm_provider, "invoke", lambda sp, um: {"ok": True, "prompt": sp})
    out = invoke_llm_agent("AUTHORED", "user")
    assert out == {"ok": True, "prompt": "AUTHORED"}


def test_harness_raises_actionable_when_unconfigured(monkeypatch):
    from reasoning.llm_harness import invoke_llm_agent
    monkeypatch.setattr(llm_provider, "available", lambda: (False, "no credentials"))
    import pytest
    with pytest.raises(NotImplementedError) as e:
        invoke_llm_agent("AUTHORED", "user")
    assert "no credentials" in str(e.value)
