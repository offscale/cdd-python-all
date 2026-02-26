import json
from openapi_client.openapi.parse import parse_openapi_dict, parse_openapi_json
from openapi_client.openapi.emit import emit_openapi_dict, emit_openapi_json
from openapi_client.models import OpenAPI


def test_openapi_parse_emit():
    spec_dict = {"openapi": "3.2.0", "info": {"title": "Test", "version": "1.0"}}
    spec_json = json.dumps(spec_dict)

    # Test parse
    parsed_dict = parse_openapi_dict(spec_dict)
    assert isinstance(parsed_dict, OpenAPI)

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
