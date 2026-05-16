def test_openapi_parse_external_refs_pointer_exception():
    import json
    from openapi_client.openapi.parse import parse_openapi_json
    from pathlib import Path

    p1 = Path("temp_spec7.json")
    p2 = Path("temp_spec8.json")
    try:
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
            }
        }
        p1.write_text(json.dumps(spec), encoding="utf-8")
        parsed = parse_openapi_json(p1.read_text(encoding="utf-8"))
        assert parsed.components.schemas["MySchema"].type == None
    finally:
        if p1.exists(): p1.unlink()
        if p2.exists(): p2.unlink()

def test_openapi_parse_external_refs_pointer_exception_2():
    import json
    from openapi_client.openapi.parse import parse_openapi_json
    from pathlib import Path

    p1 = Path("temp_spec11.json")
    p2 = Path("temp_spec12.json")
    try:
        p2.write_text('{"SomeSchema": []}', encoding="utf-8")
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "MySchema": {
                        "$ref": "temp_spec12.json#/SomeSchema/invalid_attr"
                    }
                }
            }
        }
        p1.write_text(json.dumps(spec), encoding="utf-8")
        parsed = parse_openapi_json(p1.read_text(encoding="utf-8"))
        assert parsed.components.schemas["MySchema"].ref == "temp_spec12.json#/SomeSchema/invalid_attr"
    finally:
        if p1.exists(): p1.unlink()
        if p2.exists(): p2.unlink()
