"""Phase 1: schemas validate the FNOL example."""
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def test_app_blueprint_schema_validates_fnol():
    schema = json.loads((ROOT / "schemas/app-blueprint.schema.json").read_text())
    fnol = json.loads((ROOT / "examples/fnol/outputs/app-blueprint.json").read_text())
    jsonschema.validate(fnol, schema)


def test_all_mcp_schemas_are_valid_jsonschema():
    for p in (ROOT / "schemas").glob("*.json"):
        schema = json.loads(p.read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
