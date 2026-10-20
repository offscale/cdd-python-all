"""Tests for client method emission, utilities, and AST parsing."""

from __future__ import annotations

import json
from pathlib import Path

import libcst as cst

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


def test_emit_function_formData_and_no_path_vars() -> None:
    """Test emit_function with formData parameter and no path template variables."""
    path = "/no/vars/here"
    method = "post"

    param = Parameter(
        name="my_form_param",
        in_="formData",
        required=True,
        schema=Schema(type="string"),
    )

    op = Operation(operationId="test_formData_op", parameters=[param])

    func_node = emit_function(method, path, op)
    code = cst.Module(body=[func_node]).code
    assert "def test_form_data_op(self, my_form_param: str):" in code
    assert 'url = self.base_url + "/no/vars/here"' in code
    assert 'fields = {"my_form_param": my_form_param}' in code
    assert 'self.http.request("POST", url' in code


def test_get_dummy_value_for_file() -> None:
    """Test test_get_dummy_value_for_file."""
    schema = Schema(type="file")
    val = get_dummy_value_for_schema(schema)
    assert val.value == 'b"dummy_content"'


def test_get_stub_body_ref() -> None:
    """Test get_stub_body resolves top-level $ref and emits exact dictionary elements."""
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
    code = cst.Module(body=[cst.SimpleStatementLine([cst.Expr(val)])]).code.strip()
    assert code == '{"some_prop": "test_string"}'


def test_get_stub_body_prop_ref() -> None:
    """Test get_stub_body resolves nested property $ref and nested object schemas."""
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
    code = cst.Module(body=[cst.SimpleStatementLine([cst.Expr(val)])]).code.strip()
    assert (
        code
        == '{"my_ref": {"some_prop": "test_string"}, "my_obj": {"inner": "test_string"}}'
    )


def test_emit_operation_test_param_no_schema() -> None:
    """Test test_emit_operation_test_param_no_schema."""
    param = Parameter(name="p", in_="query", type="string")
    op = Operation(operationId="test_param_type", parameters=[param])
    node = emit_operation_test("get", "/test", op)
    code = cst.Module(body=[node]).code
    assert 'client.test_param_type(p = "test_string")' in code


def test_emit_function_with_path_vars() -> None:
    """Test emit_function with hyphenated and standard path template variables."""
    path = "/users/{user-id}"
    method = "get"

    op = Operation(operationId="get_user", parameters=[])

    func_node = emit_function(method, path, op)
    code = cst.Module(body=[func_node]).code
    assert "def get_user(self):" in code
    assert 'url = self.base_url + f"/users/{user_id}"' in code


def test_emit_function_body_param() -> None:
    """Test emit_function with body parameter and parameter ordering (required before optional)."""
    op = Operation(
        operationId="create_user",
        parameters=[
            Parameter(
                name="filter",
                **{"in": "query"},
                schema=Schema(type="string", default="all"),
            ),
            Parameter(
                name="my-body",
                **{"in": "body"},
                required=True,
                schema=Schema(type="object"),
            ),
        ],
    )
    func_node = emit_function("post", "/users", op)
    code = cst.Module(body=[func_node]).code
    assert "def create_user(self, my_body: dict[str, Any], filter: str = None):" in code
    assert "json = my_body" in code


def test_sanitize_name() -> None:
    """Test sanitizing python identifiers."""
    assert sanitize_name("list-data-sets") == "list_data_sets"
    assert sanitize_name("find pet by id") == "find_pet_by_id"
    assert sanitize_name("1invalid") == "_1invalid"
    assert sanitize_name("valid_name") == "valid_name"
    assert sanitize_name("from") == "from_"
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
    """Test parsing external $ref files using base_path.

    Args:
        tmp_path: Parameter .
    """
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
    """Test parsing external $ref files with a JSON pointer fragment.

    Args:
        tmp_path: Parameter .
    """
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


def test_extract_functions_parameter_locations() -> None:
    """Test FunctionExtractor classifies path, query, header, cookie, and formData parameters accurately."""
    from openapi_client.functions.parse import (
        _extract_param_locations_from_body,
        extract_functions_from_ast,
    )

    # Test single-line body (non-IndentedBlock)
    fn_single = cst.parse_statement("def f(self): pass")
    assert isinstance(fn_single, cst.FunctionDef)
    assert _extract_param_locations_from_body(fn_single) == {}

    code = """
class Client:
    def post_upload(
        self,
        item_id: int,
        req_query: str,
        form_field: str,
        api_token: str,
        session_id: str,
    ):
        if True:
            pass
        url = self.base_url + f"/upload/{item_id}"
        fields = {"form_field": form_field, **extra}
        headers = {}
        headers["X-Api-Token"] = api_token
        cookies = {"sid": session_id}
        return self.http.request("POST", url, headers=headers, fields=fields)
"""
    spec = OpenAPI(openapi="3.2.0", info={"title": "T", "version": "1.0"}, paths={})
    extract_functions_from_ast(cst.parse_module(code), spec)
    assert spec.paths is not None
    op = spec.paths["/upload/{item_id}"].post
    assert op is not None
    assert op.parameters is not None
    by_name = {p.name: p.in_ for p in op.parameters if isinstance(p, Parameter)}
    assert by_name == {
        "item_id": "path",
        "req_query": "query",
        "form_field": "formData",
        "X-Api-Token": "header",
        "sid": "cookie",
    }
