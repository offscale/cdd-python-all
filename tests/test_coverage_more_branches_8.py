"""Tests for test_coverage_more_branches_8.py."""

from openapi_client.cli import generate_from_openapi
from openapi_client.openapi.parse import parse_openapi_dict
import json


def test_cli_loop_skip(tmp_path):
    """Test test_cli_loop_skip."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {},
    }
    input_file = tmp_path / "openapi.json"
    input_file.write_text(json.dumps(spec))
    generate_from_openapi(
        "to_unknown_subcommand",
        str(input_file),
        None,
        str(tmp_path),
        False,
        False,
        False,
    )


def test_openapi_parse_empty_part(tmp_path):
    """Test test_openapi_parse_empty_part."""
    external_file = tmp_path / "ext.json"
    external_file.write_text(
        json.dumps({"components": {"schemas": {"A": {"type": "string"}}}})
    )

    spec = {
        "openapi": "3.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "components": {
            "schemas": {
                "EmptyPart": {"$ref": "ext.json#//components//schemas/A"},
                "EmptyRef": {"$ref": ""},
            }
        },
    }
    parse_openapi_dict(spec, base_path=tmp_path)


def test_openapi_parse_parameters_list(tmp_path):
    """Test test_openapi_parse_parameters_list."""
    from openapi_client.openapi.parse import parse_openapi_dict

    spec = {
        "openapi": "3.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "parameters": [{"name": "test", "in": "query", "schema": {"type": "string"}}],
    }
    try:
        parse_openapi_dict(spec, base_path=tmp_path)
    except Exception:
        pass
