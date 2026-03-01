import pytest
from pathlib import Path
from openapi_client.functions.utils import get_annotation_for_schema
from openapi_client.models import Schema
from openapi_client.openapi.parse import resolve_external_refs, parse_openapi_json
import libcst as cst
from openapi_client.tests.parse import ASTTestExtractor
from openapi_client.models import OpenAPI


def test_get_annotation_for_schema():
    assert get_annotation_for_schema(None) == "Any"
    assert get_annotation_for_schema(Schema(type="string")) == "str"
    assert get_annotation_for_schema(Schema(type="integer")) == "int"
    assert get_annotation_for_schema(Schema(type="number")) == "float"
    assert get_annotation_for_schema(Schema(type="boolean")) == "bool"
    assert (
        get_annotation_for_schema(Schema(type="array", items=Schema(type="object")))
        == "List[Dict[str, Any]]"
    )
    assert get_annotation_for_schema(Schema(type="object")) == "Dict[str, Any]"
    assert get_annotation_for_schema(Schema(type="unknown")) == "Any"


def test_resolve_external_refs(tmp_path):
    external_file = tmp_path / "external.json"
    external_file.write_text('{"target": {"val": 42}}')

    spec = {
        "a": {"$ref": "external.json#/target"},
        "b": [{"$ref": "missing.json#/nothing"}],
    }
    resolved = resolve_external_refs(spec, base_path=tmp_path)
    assert resolved["a"] == {"val": 42}
    assert resolved["b"][0]["$ref"] == "missing.json#/nothing"


def test_parse_openapi_json_with_ref(tmp_path):
    external = tmp_path / "ext.json"
    external.write_text('{"title": "Resolved API", "version": "1.0"}')
    json_str = '{"openapi": "3.2.0", "info": {"$ref": "ext.json#"}}'
    spec = parse_openapi_json(json_str, base_path=tmp_path)
    assert spec.info.title == "Resolved API"


def test_test_extractor_sse():
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = ASTTestExtractor(spec)
    module = cst.parse_module(
        "def test_stream_something():\n"
        "    assert 'text/event-stream' in res\n"
        "def test_normal():\n"
        "    pass\n"
    )
    module.visit(extractor)


def test_resolve_external_refs_exception(tmp_path):
    external_file = tmp_path / "bad.json"
    external_file.write_text("bad json content")

    spec = {
        "a": {"$ref": "bad.json#/target"},
    }
    resolved = resolve_external_refs(spec, base_path=tmp_path)
    assert resolved["a"]["$ref"] == "bad.json#/target"
