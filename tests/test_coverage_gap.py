"""Tests for test_coverage_gap.py."""

import pytest

from openapi_client.models import OpenAPI, Schema, Reference, Components
from openapi_client.classes.emit import emit_classes
from openapi_client.classes.parse import ClassExtractor
from openapi_client.functions.parse import FunctionExtractor
from openapi_client.mocks.parse import MockServerExtractor
import libcst as cst


def test_classes_emit_ref():
    """Test test_classes_emit_ref."""
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        components={
            "schemas": {
                "MyClass": Schema(
                    **{
                        "type": "object",
                        "properties": {
                            "my_ref": Reference(
                                **{"$ref": "#/components/schemas/Other"}
                            )
                        },
                    }
                )
            }
        },
    )
    defs = emit_classes(spec.components.schemas)
    assert len(defs) == 1


def test_classes_parse_empty_components():
    """Test test_classes_parse_empty_components."""
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        components=Components(),
    )
    extractor = ClassExtractor(spec)
    module = cst.parse_module("class MyClass:\n    pass\n")
    module.visit(extractor)
    assert "MyClass" in spec.components.schemas


def test_functions_parse_empty_paths():
    """Test test_functions_parse_empty_paths."""
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = FunctionExtractor(spec)
    module = cst.parse_module("def get_pets():\n    pass\n")
    module.visit(extractor)
    assert "/pets" in spec.paths


def test_mocks_parse_empty_paths():
    """Test test_mocks_parse_empty_paths."""
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = MockServerExtractor(spec)
    module = cst.parse_module("@app.get('/pets')\ndef my_mock():\n    pass\n")
    module.visit(extractor)
    assert "/pets" in spec.paths


def test_functions_parse_full_features():
    """Test test_functions_parse_full_features."""
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = FunctionExtractor(spec)
    code = """
@tags(['Users'])
@deprecated
def post_user(user_id: str, limit: int = 10, is_active: bool = True, ratio: float = 1.0, tags: list[str] = [], extra: dict[str, str] = {}, data: MyBody = None) -> MyResponse:
    '''
    Create User

    Creates a new user object.
    '''
    pass
"""
    module = cst.parse_module(code)
    module.visit(extractor)

    op = spec.paths["/user"].post
    assert op.operationId == "post_user"
    assert op.summary == "Create User"
    assert op.description == "Creates a new user object."
    assert op.deprecated is True
    assert "Users" in op.tags

    # Check parameters
    assert len(op.parameters) == 6
    params = {p.name: p for p in op.parameters}
    assert params["user_id"].in_ == "path"
    assert params["user_id"].required is True
    assert params["user_id"].schema_.type == "string"

    assert params["limit"].in_ == "query"
    assert params["limit"].required is False
    assert params["limit"].schema_.type == "integer"

    assert params["is_active"].schema_.type == "boolean"
    assert params["ratio"].schema_.type == "number"
    assert params["tags"].schema_.type == "array"
    assert params["tags"].schema_.items.type == "string"

    assert params["extra"].schema_.type == "object"

    # Check request body
    assert op.requestBody is not None
    assert op.requestBody.required is False
    assert (
        op.requestBody.content["application/json"].schema_.ref
        == "#/components/schemas/MyBody"
    )

    # Check response
    assert op.responses is not None
    assert (
        op.responses["200"].content["application/json"].schema_.ref
        == "#/components/schemas/MyResponse"
    )


def test_functions_parse_fallback_annotation():
    """Test test_functions_parse_fallback_annotation."""
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = FunctionExtractor(spec)
    code = """
def post_user(arg: "ForwardRef"):
    pass
"""
    module = cst.parse_module(code)
    module.visit(extractor)
    op = spec.paths["/user"].post
    assert op.parameters[0].schema_.type == "string"


def test_mcp_get_prompt():
    """Test get_prompt."""
    from openapi_client.mcp import get_prompt

    prompt = get_prompt("generate_tests", {"component": "TestComponent"})
    assert prompt["description"] == "Generate tests for TestComponent"
    assert "TestComponent" in prompt["messages"][0]["content"]["text"]

    with pytest.raises(ValueError):
        get_prompt("unknown_prompt", {})


def test_mcp_get_prompts():
    """Test get_prompts."""
    from openapi_client.mcp import get_prompts

    prompts = get_prompts()
    assert len(prompts) == 1
    assert prompts[0]["name"] == "generate_tests"


def test_mcp_read_resource_error():
    """Test read_resource error."""
    from openapi_client.mcp import read_resource

    with pytest.raises(ValueError):
        read_resource("invalid://uri")


def test_mcp_client_notifications():
    """Test building various notifications."""
    from openapi_client.mcp_client.client import MCPClient

    client = MCPClient()
    assert client.build_cancelled_notification(1)["method"] == "notifications/cancelled"
    assert (
        client.build_progress_notification("token", 0.5)["method"]
        == "notifications/progress"
    )
    assert (
        client.build_roots_list_changed_notification()["method"]
        == "notifications/roots/list_changed"
    )
    assert (
        client.build_logging_message_notification("info", "logger", "data")["method"]
        == "notifications/message"
    )
    assert (
        client.build_resource_updated_notification("uri")["method"]
        == "notifications/resources/updated"
    )
    assert (
        client.build_resource_list_changed_notification()["method"]
        == "notifications/resources/list_changed"
    )
    assert (
        client.build_tool_list_changed_notification()["method"]
        == "notifications/tools/list_changed"
    )
    assert (
        client.build_prompt_list_changed_notification()["method"]
        == "notifications/prompts/list_changed"
    )


def test_mcp_client_cursor():
    """Test building various requests with cursor."""
    from openapi_client.mcp_client.client import MCPClient

    client = MCPClient()
    assert (
        client.build_list_resource_templates_request("cursor")["params"]["cursor"]
        == "cursor"
    )


def test_mcp_client_more_methods():
    """Test test_mcp_client_more_methods."""
    from openapi_client.mcp_client.client import MCPClient

    client = MCPClient()
    assert client.build_ping_request()["method"] == "ping"
    assert client.build_initialize_request()["method"] == "initialize"
    assert client.build_set_level_request("info")["method"] == "logging/setLevel"
    assert client.build_list_resources_request()["method"] == "resources/list"
    assert client.build_read_resource_request("uri")["method"] == "resources/read"
    assert client.build_list_prompts_request()["method"] == "prompts/list"
    assert client.build_get_prompt_request("name", {})["method"] == "prompts/get"
    assert client.build_list_tools_request()["method"] == "tools/list"
    assert client.build_call_tool_request("name", {})["method"] == "tools/call"

    assert client.build_list_resources_request("c")["params"]["cursor"] == "c"
    assert client.build_list_prompts_request("c")["params"]["cursor"] == "c"
    assert client.build_list_tools_request("c")["params"]["cursor"] == "c"
    assert client.build_list_resource_templates_request("c")["params"]["cursor"] == "c"


def test_mcp_all_methods():
    """Test test_mcp_all_methods."""
    from openapi_client.mcp import get_tools, execute_tool, get_resources, read_resource

    assert len(get_tools()) == 3
    assert len(get_resources()) == 1
    assert read_resource("schema://current")["openapi"] == "3.0.0"

    import openapi_client.sdk as sdk

    # Just mock the sdk functions temporarily
    old_to = getattr(sdk, "generate_to_openapi", None)
    old_from = getattr(sdk, "generate_from_openapi", None)
    old_docs = getattr(sdk, "generate_docs_json", None)

    setattr(sdk, "generate_to_openapi", lambda **kwargs: "to")
    setattr(sdk, "generate_from_openapi", lambda **kwargs: "from")
    setattr(sdk, "generate_docs_json", lambda **kwargs: "docs")

    try:
        assert execute_tool("to_openapi", {"input_dir": "test"}) == "to"
        assert (
            execute_tool("from_openapi", {"input_path": "test", "output_dir": "test"})
            == "from"
        )
        assert execute_tool("to_docs_json", {"input_path": "test"}) == "docs"
        with pytest.raises(ValueError):
            execute_tool("unknown", {})
    finally:
        if old_to:
            setattr(sdk, "generate_to_openapi", old_to)
        if old_from:
            setattr(sdk, "generate_from_openapi", old_from)
        if old_docs:
            setattr(sdk, "generate_docs_json", old_docs)


def test_mcp_client_more_missing():
    """Test test_mcp_client_more_missing."""
    from openapi_client.mcp_client.client import MCPClient

    client = MCPClient()
    assert (
        client.build_initialized_notification()["method"] == "notifications/initialized"
    )


def test_mcp_client_cursor_none_no_params():
    """Test test_mcp_client_cursor_none_no_params."""
    from openapi_client.mcp_client.client import MCPClient

    client = MCPClient()

    assert "params" not in client.build_list_resource_templates_request()
