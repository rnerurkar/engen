"""Every live-service boundary: injectable seam works; the live call is written but commented
out and raises NotImplementedError when not wired (no fabrication)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/solution-accelerator/src"))


def test_vertex_search_seam_and_unwired_raises():
    import pytest
    from clients.vertex_search import VertexSearchClient
    c = VertexSearchClient(_search=lambda ds, q: [{"id": "p1"}])
    assert c.search_patterns(["a"]) == [{"id": "p1"}]
    with pytest.raises(NotImplementedError):
        VertexSearchClient().search_patterns(["x"])


def test_apigee_hub_seam_and_unwired_raises():
    import pytest
    from clients.apigee_hub import ApigeeHubClient
    c = ApigeeHubClient(_search=lambda f: [])
    assert c.search(api_type="a2a_agent") == []
    with pytest.raises(NotImplementedError):
        ApigeeHubClient().search(api_type="a2a_agent")


def test_eraser_mcp_seam_and_unwired_raises():
    import pytest
    from clients.eraser_mcp import EraserMcpClient
    c = EraserMcpClient(_render=lambda dsl: {"drawio_xml": "<x/>", "png_base64": "AA"})
    r = c.render("dsl")
    assert r.drawio_xml == "<x/>"
    with pytest.raises(NotImplementedError):
        EraserMcpClient().render("dsl")


def test_alloydb_seam_schema_and_unwired_raises():
    import pytest
    from clients.alloydb_taskstore import SCHEMA_DDL, AlloydbTaskstoreClient
    assert SCHEMA_DDL.count("CREATE TABLE") == 3   # tasks + blueprint + findings pointers
    c = AlloydbTaskstoreClient(_execute=lambda sql, p: [("t1",)])
    assert c.execute("SELECT 1") == [("t1",)]
    with pytest.raises(NotImplementedError):
        AlloydbTaskstoreClient().execute("SELECT 1")


def test_gcs_client_reference_backing_and_unwired_get_raises():
    import pytest
    from clients.gcs_client import GcsClient
    g = GcsClient()
    g.put("gs://b/x.md", "hello")           # reference backing (live put commented out)
    assert g.get("gs://b/x.md") == b"hello"
    with pytest.raises(NotImplementedError):
        GcsClient().get("gs://b/missing")   # unwired + absent -> raises


def test_gemini_seam_and_unwired_raises():
    import pytest
    from reasoning.llm_harness import invoke_llm_agent
    out = invoke_llm_agent("sys", "user", model_fn=lambda s, u: {"ok": True})
    assert out == {"ok": True}
    with pytest.raises(NotImplementedError):
        invoke_llm_agent("sys", "user")     # no model_fn, live call commented out
