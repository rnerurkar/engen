"""Live LLM provider for recommend_architecture reasoning.

This is the WIRED live path (not commented out). It calls Gemini via the google-genai SDK,
requesting JSON output, and returns the parsed dict. It is guarded so it degrades cleanly:
  - if the SDK isn't installed OR no credentials/project are configured, `available()` is False
    and callers fall back to the injected model_fn (tests) or surface a clear, actionable error.

Config via env:
  SDLC_LLM_MODEL          (default: gemini-2.5-pro)
  GOOGLE_CLOUD_PROJECT    (Vertex AI project; required for Vertex backend)
  GOOGLE_CLOUD_LOCATION   (default: us-central1)
  GOOGLE_GENAI_USE_VERTEXAI=true   (use Vertex AI backend; ADC credentials)
  GEMINI_API_KEY          (alternative: direct Gemini API instead of Vertex)

The system_prompt is the human-authored curated reasoning prompt — bound verbatim as the
instruction. This module does NOT author or mutate reasoning content.
"""
from __future__ import annotations

import json
import os

from clients.base import with_retry

DEFAULT_MODEL = "gemini-2.5-pro"


def _model() -> str:
    return os.environ.get("SDLC_LLM_MODEL", DEFAULT_MODEL)


def available() -> tuple[bool, str]:
    """Is the live LLM path usable here? Returns (ok, reason-if-not)."""
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return False, "google-genai not installed (pip install google-genai)"
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    if use_vertex:
        if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
            return False, "GOOGLE_CLOUD_PROJECT not set (required for Vertex AI backend)"
        return True, ""
    if os.environ.get("GEMINI_API_KEY"):
        return True, ""
    return False, ("no credentials: set GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT "
                   "(Vertex AI + ADC), or GEMINI_API_KEY (direct Gemini API)")


def _build_client():
    from google import genai
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    if use_vertex:
        return genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def invoke(system_prompt: str, user_message: str) -> dict:
    """Live Gemini call. Returns the parsed JSON dict the recommend parser expects.

    Raises RuntimeError with an actionable message if the path isn't configured."""
    ok, reason = available()
    if not ok:
        raise RuntimeError(f"Live LLM not available: {reason}")

    from google.genai import types

    client = _build_client()

    def _call() -> dict:
        resp = client.models.generate_content(
            model=_model(),
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,   # authored prompt, verbatim
                response_mime_type="application/json",
                temperature=0.2,                     # low temp: reasoning should be stable
            ),
        )
        return json.loads(resp.text)

    return with_retry(_call)
