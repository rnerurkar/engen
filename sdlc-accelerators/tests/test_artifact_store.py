"""Blueprint artifact store: all artifacts in GCS, one pointer in AlloyDB, read-back combines
md + json + diagrams for the IDE. Mirrors the findings-store pattern."""
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/solution-accelerator/src"))

from artifact_store.store import BlueprintArtifactStore


def _diagrams():
    return [
        {"name": "component-topology", "drawio_xml": "<mxGraphModel/>",
         "png_base64": base64.b64encode(b"PNG1").decode()},
        {"name": "hadr-lifecycle", "drawio_xml": "<mxGraphModel id='2'/>",
         "png_base64": base64.b64encode(b"PNG2").decode()},
    ]


def test_write_creates_pointer_and_manifest():
    store = BlueprintArtifactStore(bucket="bp")
    ptr = store.write_blueprint("t1", "dev@co", "# MD", {"k": "v"}, _diagrams())
    assert ptr.gcs_prefix == "gs://bp/blueprints/dev@co/t1/"
    assert ptr.owner_id == "dev@co"
    assert [d["name"] for d in ptr.manifest.diagrams] == ["component-topology", "hadr-lifecycle"]


def test_read_back_combines_md_json_diagrams():
    store = BlueprintArtifactStore(bucket="bp")
    store.write_blueprint("t1", "dev@co", "# Blueprint", {"archetype": "agentic"}, _diagrams())
    bp = store.read_blueprint("t1")
    assert bp["markdown"] == "# Blueprint"
    assert bp["json"] == {"archetype": "agentic"}
    assert len(bp["diagrams"]) == 2
    # png round-trips through base64
    assert base64.b64decode(bp["diagrams"][0]["png_base64"]) == b"PNG1"
    assert bp["diagrams"][0]["drawio_xml"] == "<mxGraphModel/>"
    # each diagram carries its GCS uri
    assert bp["diagrams"][0]["gcs_uri"].endswith("component-topology.png")


def test_gcs_put_seam_receives_all_artifacts():
    store = BlueprintArtifactStore(bucket="bp")
    puts = {}
    store.write_blueprint("t1", "dev@co", "# MD", {"k": "v"}, _diagrams(),
                          _gcs_put=lambda uri, data: puts.__setitem__(uri, data))
    # md + json + 2 drawio + 2 png = 6 objects
    assert len(puts) == 6
    assert any(u.endswith("app-blueprint.md") for u in puts)
    assert any(u.endswith("app-blueprint.json") for u in puts)
    assert sum(1 for u in puts if u.endswith(".png")) == 2
    assert sum(1 for u in puts if u.endswith(".drawio.xml")) == 2


def test_png_stored_as_bytes_not_base64_in_object():
    """PNGs go to GCS as decoded bytes (object storage), not base64-in-DB."""
    store = BlueprintArtifactStore(bucket="bp")
    puts = {}
    store.write_blueprint("t1", "dev@co", "# MD", {}, _diagrams(),
                          _gcs_put=lambda uri, data: puts.__setitem__(uri, data))
    png_obj = next(v for u, v in puts.items() if u.endswith("component-topology.png"))
    assert png_obj == b"PNG1"   # raw bytes, not base64
