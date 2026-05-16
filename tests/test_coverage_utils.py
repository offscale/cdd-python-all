from openapi_client.functions.utils import sanitize_name


def test_sanitize_name():
    """Test sanitizing python identifiers."""
    assert sanitize_name("list-data-sets") == "list_data_sets"
    assert sanitize_name("find pet by id") == "find_pet_by_id"
    assert sanitize_name("1invalid") == "_1invalid"
    assert sanitize_name("valid_name") == "valid_name"
    assert sanitize_name("") == ""

def test_get_dummy_value_for_schema():
    from openapi_client.tests.emit import get_dummy_value_for_schema
    from openapi_client.models import Schema

    assert get_dummy_value_for_schema(None).value == "None"
    assert get_dummy_value_for_schema(Schema(type="boolean")).value == "True"
    assert get_dummy_value_for_schema(Schema(type="array", items=Schema(type="integer"))).elements[0].value.value == "1"
    assert get_dummy_value_for_schema(Schema(type="object")).elements == []
    assert get_dummy_value_for_schema(Schema(type="array")).elements == []

def test_openapi_parse_external_refs():
    import json
    from openapi_client.openapi.parse import parse_openapi_json
    from pathlib import Path

    p1 = Path("temp_spec1.json")
    p2 = Path("temp_spec2.json")
    try:
        p2.write_text('{"type": "string", "example": "hello"}', encoding="utf-8")
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "MySchema": {
                        "$ref": "temp_spec2.json"
                    }
                }
            }
        }
        p1.write_text(json.dumps(spec), encoding="utf-8")
        parsed = parse_openapi_json(p1.read_text(encoding="utf-8"))
        assert parsed.components.schemas["MySchema"].type == "string"
    finally:
        if p1.exists(): p1.unlink()
        if p2.exists(): p2.unlink()

def test_openapi_parse_external_refs_with_pointer():
    import json
    from openapi_client.openapi.parse import parse_openapi_json
    from pathlib import Path

    p1 = Path("temp_spec3.json")
    p2 = Path("temp_spec4.json")
    try:
        p2.write_text('{"SomeSchema": {"type": "integer"}}', encoding="utf-8")
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "MySchema": {
                        "$ref": "temp_spec4.json#/SomeSchema"
                    }
                }
            }
        }
        p1.write_text(json.dumps(spec), encoding="utf-8")
        parsed = parse_openapi_json(p1.read_text(encoding="utf-8"))
        assert parsed.components.schemas["MySchema"].type == "integer"
    finally:
        if p1.exists(): p1.unlink()
        if p2.exists(): p2.unlink()

def test_emit_function_body_param():
    from openapi_client.functions.emit import emit_function
    from openapi_client.models import Operation, Parameter, Schema

    op = Operation(
        operationId="test_body_param",
        parameters=[Parameter(name="my_body", in_="body", schema=Schema(type="string"))]
    )
    func_def = emit_function("post", "/test", op)
    assert func_def.name.value == "test_body_param"


def test_openapi_parse_external_refs_exception():
    import json
    from openapi_client.openapi.parse import parse_openapi_json
    from pathlib import Path

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "MySchema": {
                    "$ref": "non_existent_file.json"
                }
            }
        }
    }
    parsed = parse_openapi_json(json.dumps(spec))
    assert parsed.components.schemas["MySchema"].ref == "non_existent_file.json"


def test_openapi_parse_external_refs_array():
    import json
    from openapi_client.openapi.parse import parse_openapi_json
    
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "MySchema": {
                    "type": "array",
                    "items": [
                        {"$ref": "non_existent.json"}
                    ]
                }
            }
        }
    }
    parsed = parse_openapi_json(json.dumps(spec))
    assert parsed.components.schemas["MySchema"].items[0].ref == "non_existent.json"
