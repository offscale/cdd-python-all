"""Tests for OpenAPI JSON/dict parsing, emission, and external $ref resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openapi_client.exceptions import ReferenceResolutionError, SpecificationParseError
from openapi_client.models import OpenAPI
from openapi_client.openapi.emit import emit_openapi_dict, emit_openapi_json
from openapi_client.openapi.parse import parse_openapi_dict, parse_openapi_json


def test_openapi_parse_emit() -> None:
    """Test OpenAPI dict/JSON parsing, deep-copy isolation, and emission."""
    spec_dict = {"openapi": "3.2.0", "info": {"title": "Test", "version": "1.0"}}
    spec_json = json.dumps(spec_dict)

    # Test parse and verify caller's dict is not mutated with 'components'
    parsed_dict = parse_openapi_dict(spec_dict)
    assert isinstance(parsed_dict, OpenAPI)
    assert "components" not in spec_dict

    parsed_json = parse_openapi_json(spec_json)
    assert isinstance(parsed_json, OpenAPI)
    assert parsed_json.openapi == "3.2.0"

    # Test emit
    emitted_dict = emit_openapi_dict(parsed_dict)
    assert emitted_dict["openapi"] == "3.2.0"
    assert emitted_dict["info"]["title"] == "Test"

    emitted_json = emit_openapi_json(parsed_json)
    assert "3.2.0" in emitted_json
    assert "Test" in emitted_json

    with pytest.raises(SpecificationParseError):
        parse_openapi_json("{invalid json")


def test_openapi_swagger2_parse() -> None:
    """Test Swagger 2.0 normalization into OpenAPI components."""
    spec_dict = {
        "swagger": "2.0",
        "info": {"title": "Swagger 2", "version": "1.0"},
        "definitions": {"MyModel": {"type": "object"}},
        "securityDefinitions": {
            "api_key": {"type": "apiKey", "name": "api_key", "in": "header"}
        },
        "parameters": {"skipParam": {"name": "skip", "in": "query", "type": "integer"}},
        "responses": {"Unauthorized": {"description": "Unauthorized"}},
    }
    parsed_dict = parse_openapi_dict(spec_dict)
    assert parsed_dict.swagger == "2.0"
    assert parsed_dict.components is not None
    assert parsed_dict.components.schemas is not None
    assert parsed_dict.components.securitySchemes is not None
    assert parsed_dict.components.parameters is not None
    assert parsed_dict.components.responses is not None
    assert "MyModel" in parsed_dict.components.schemas
    assert "api_key" in parsed_dict.components.securitySchemes
    assert "skipParam" in parsed_dict.components.parameters
    assert "Unauthorized" in parsed_dict.components.responses


def test_openapi_parse_external_refs_pointer_exception(tmp_path: Path) -> None:
    """Test external $ref resolution when pointer path traverses missing keys.

    Args:
        tmp_path: Parameter .
    """
    p1 = tmp_path / "temp_spec7.json"
    p2 = tmp_path / "temp_spec8.json"
    p2.write_text('{"SomeSchema": {"type": "integer"}}', encoding="utf-8")
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "MySchema": {
                    "$ref": "temp_spec8.json#/SomeSchema/non_existent_key/more"
                }
            }
        },
    }
    p1.write_text(json.dumps(spec), encoding="utf-8")
    parsed = parse_openapi_json(p1.read_text(encoding="utf-8"), base_path=tmp_path)
    assert parsed.components is not None
    assert parsed.components.schemas is not None
    assert parsed.components.schemas["MySchema"].type is None


def test_openapi_parse_external_refs_pointer_exception_2(tmp_path: Path) -> None:
    """Test external $ref resolution when pointer traverses a non-dict object.

    Args:
        tmp_path: Parameter .
    """
    p1 = tmp_path / "temp_spec11.json"
    p2 = tmp_path / "temp_spec12.json"
    p2.write_text('{"SomeSchema": []}', encoding="utf-8")
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "MySchema": {"$ref": "temp_spec12.json#/SomeSchema/invalid_attr"}
            }
        },
    }
    p1.write_text(json.dumps(spec), encoding="utf-8")
    parsed = parse_openapi_json(p1.read_text(encoding="utf-8"), base_path=tmp_path)
    assert parsed.components is not None
    assert parsed.components.schemas is not None
    assert (
        parsed.components.schemas["MySchema"].ref
        == "temp_spec12.json#/SomeSchema/invalid_attr"
    )


def test_openapi_parse_external_refs_security_and_invalid_json(
    tmp_path: Path,
) -> None:
    """Test path traversal protection and invalid JSON error reporting in resolve_external_refs.

    Args:
        tmp_path: Parameter .
    """
    sub_dir = tmp_path / "nested"
    sub_dir.mkdir()

    escape_spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "components": {"schemas": {"Bad": {"$ref": "../secret.json"}}},
    }
    with pytest.raises(ReferenceResolutionError, match="escapes allowed root"):
        parse_openapi_dict(escape_spec, base_path=sub_dir)

    bad_json_file = sub_dir / "corrupt.json"
    bad_json_file.write_text("{corrupt", encoding="utf-8")
    corrupt_spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "components": {"schemas": {"Bad": {"$ref": "corrupt.json"}}},
    }
    with pytest.raises(ReferenceResolutionError, match="Invalid JSON"):
        parse_openapi_dict(corrupt_spec, base_path=sub_dir)
