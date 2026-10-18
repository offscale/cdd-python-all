"""Tests for client method emission, utilities, and AST parsing."""

from __future__ import annotations

import json
from pathlib import Path

from openapi_client.functions.emit import emit_function
from openapi_client.functions.utils import sanitize_name
from openapi_client.models import (
    Components,
    OpenAPI,
    Operation,
    Parameter,
    Reference,
    Schema,
)
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.tests.emit import (
    emit_operation_test,
    get_dummy_value_for_schema,
    get_stub_body,
)


def test_emit_function_formData_and_no_path_vars():
    # Test path without "{}"
    """Test test_emit_function_formData_and_no_path_vars."""
    path = "/no/vars/here"
    method = "post"

    # Test param with in="formData"
    param = Parameter(
        name="my_form_param",
        in_="formData",
        required=True,
        schema=Schema(type="string"),
    )

    op = Operation(operationId="test_formData_op", parameters=[param])

    func_node = emit_function(method, path, op)
    assert func_node is not None
    assert func_node.name.value == "test_form_data_op"


def test_get_dummy_value_for_file():
    """Test test_get_dummy_value_for_file."""
    schema = Schema(type="file")
    val = get_dummy_value_for_schema(schema)
    assert val.value == 'b"dummy_content"'


def test_get_stub_body_ref():
    """Test test_get_stub_body_ref."""
    ref_schema = Reference(ref="#/components/schemas/Target")
    target_schema = Schema(
        type="object", properties={"some_prop": Schema(type="string")}
    )
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={},
        components=Components(schemas={"Target": target_schema}),
    )
    val = get_stub_body(ref_schema, spec)
    assert val is not None


def test_get_stub_body_prop_ref():
    """Test test_get_stub_body_prop_ref."""
    ref_schema = Reference(ref="#/components/schemas/Target")
    target_schema = Schema(
        type="object", properties={"some_prop": Schema(type="string")}
    )
    main_schema = Schema(
        type="object",
        properties={
            "my_ref": ref_schema,
            "my_obj": Schema(
                type="object", properties={"inner": Schema(type="string")}
            ),
        },
    )
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={},
        components=Components(schemas={"Target": target_schema}),
    )
    val = get_stub_body(main_schema, spec)
    assert val is not None


def test_emit_operation_test_param_no_schema():
    """Test test_emit_operation_test_param_no_schema."""
    param = Parameter(name="p", in_="query", type="string")
    op = Operation(operationId="test_param_type", parameters=[param])
    node = emit_operation_test("get", "/test", op)
    assert node is not None


def test_emit_function_with_path_vars():
    """Test test_emit_function_with_path_vars."""
    path = "/users/{id}"
    method = "get"

    op = Operation(operationId="get_user", parameters=[])

    func_node = emit_function(method, path, op)
    assert func_node is not None
    assert func_node.name.value == "get_user"


def test_sanitize_name() -> None:
    """Test sanitizing python identifiers."""
    assert sanitize_name("list-data-sets") == "list_data_sets"
    assert sanitize_name("find pet by id") == "find_pet_by_id"
    assert sanitize_name("1invalid") == "_1invalid"
    assert sanitize_name("valid_name") == "valid_name"
    assert sanitize_name("") == ""


def test_get_dummy_value_for_schema() -> None:
    """Test get_dummy_value_for_schema for various schema types."""
    assert get_dummy_value_for_schema(None).value == "None"
    assert get_dummy_value_for_schema(Schema(type="boolean")).value == "True"
    assert (
        get_dummy_value_for_schema(Schema(type="array", items=Schema(type="integer")))
        .elements[0]
        .value.value
        == "1"
    )
    assert get_dummy_value_for_schema(Schema(type="object")).elements == []
    assert get_dummy_value_for_schema(Schema(type="array")).elements == []


def test_openapi_parse_external_refs(tmp_path: Path) -> None:
    """Test parsing external $ref files using base_path."""
    p1 = tmp_path / "temp_spec1.json"
    p2 = tmp_path / "temp_spec2.json"
    p2.write_text('{"type": "string", "example": "hello"}', encoding="utf-8")
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {"MySchema": {"$ref": "temp_spec2.json"}}},
    }
    p1.write_text(json.dumps(spec), encoding="utf-8")
    parsed = parse_openapi_json(p1.read_text(encoding="utf-8"), base_path=tmp_path)
    assert parsed.components is not None
    assert parsed.components.schemas is not None
    assert parsed.components.schemas["MySchema"].type == "string"


def test_openapi_parse_external_refs_with_pointer(tmp_path: Path) -> None:
    """Test parsing external $ref files with a JSON pointer fragment."""
    p1 = tmp_path / "temp_spec3.json"
    p2 = tmp_path / "temp_spec4.json"
    p2.write_text('{"SomeSchema": {"type": "integer"}}', encoding="utf-8")
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {"MySchema": {"$ref": "temp_spec4.json#/SomeSchema"}}
        },
    }
    p1.write_text(json.dumps(spec), encoding="utf-8")
    parsed = parse_openapi_json(p1.read_text(encoding="utf-8"), base_path=tmp_path)
    assert parsed.components is not None
    assert parsed.components.schemas is not None
    assert parsed.components.schemas["MySchema"].type == "integer"


def test_emit_function_body_param() -> None:
    """Test emit_function with a Swagger 2.0 style in=body parameter."""
    op = Operation(
        operationId="test_body_param",
        parameters=[
            Parameter(name="my_body", in_="body", schema=Schema(type="string"))
        ],
    )
    func_def = emit_function("post", "/test", op)
    assert func_def.name.value == "test_body_param"


def test_openapi_parse_external_refs_exception() -> None:
    """Test parse_openapi_json when an external $ref file does not exist."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {"MySchema": {"$ref": "non_existent_file.json"}}},
    }
    parsed = parse_openapi_json(json.dumps(spec))
    assert parsed.components is not None
    assert parsed.components.schemas is not None
    assert parsed.components.schemas["MySchema"].ref == "non_existent_file.json"


def test_openapi_parse_external_refs_array() -> None:
    """Test parse_openapi_json when an array items list contains an external $ref."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "MySchema": {"type": "array", "items": [{"$ref": "non_existent.json"}]}
            }
        },
    }
    parsed = parse_openapi_json(json.dumps(spec))
    assert parsed.components is not None
    assert parsed.components.schemas is not None
    assert parsed.components.schemas["MySchema"].items[0].ref == "non_existent.json"
