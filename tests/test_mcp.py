"""Tests for the MCP adapter, MCPClient, and SDK programmatic entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import libcst as cst
import pytest

from openapi_client import sdk
from openapi_client.classes.emit import emit_classes
from openapi_client.classes.parse import ClassExtractor
from openapi_client.functions.parse import FunctionExtractor
from openapi_client.mcp_client.client import MCPClient
from openapi_client.mocks.parse import MockServerExtractor
from openapi_client.models import Components, OpenAPI, Reference, Schema


def test_mcp_client_build_request():
    """Test test_mcp_client_build_request."""
    client = MCPClient()
    req = client.build_request("test/method", {"foo": "bar"})
    assert req["jsonrpc"] == "2.0"
    assert req["method"] == "test/method"
    assert req["params"] == {"foo": "bar"}
    assert req["id"] == 1


def test_mcp_client_parse_response():
    """Test test_mcp_client_parse_response."""
    client = MCPClient()
    res = client.parse_response(
        '{"jsonrpc": "2.0", "result": {"success": true}, "id": 1}'
    )
    assert res["jsonrpc"] == "2.0"
    assert res["result"]["success"] is True


def test_mcp_client_build_call_tool():
    """Test test_mcp_client_build_call_tool."""
    client = MCPClient()
    req = client.build_call_tool_request("my_tool", {"arg1": 1})
    assert req["method"] == "tools/call"
    assert req["params"]["name"] == "my_tool"
    assert req["params"]["arguments"] == {"arg1": 1}


def test_mcp_client_build_initialize():
    """Test test_mcp_client_build_initialize."""
    client = MCPClient()
    req = client.build_initialize_request()
    assert req["method"] == "initialize"
    assert "protocolVersion" in req["params"]
    assert "clientInfo" in req["params"]


def test_mcp_client_build_notification():
    """Test test_mcp_client_build_notification."""
    client = MCPClient()
    notif = client.build_notification("notifications/initialized", {})
    assert notif["jsonrpc"] == "2.0"
    assert notif["method"] == "notifications/initialized"
    assert "id" not in notif


def test_mcp_client_build_subscribe():
    """Test test_mcp_client_build_subscribe."""
    client = MCPClient()
    req = client.build_subscribe_request("schema://foo")
    assert req["method"] == "resources/subscribe"
    assert req["params"]["uri"] == "schema://foo"


def test_mcp_client_build_unsubscribe():
    """Test test_mcp_client_build_unsubscribe."""
    client = MCPClient()
    req = client.build_unsubscribe_request("schema://bar")
    assert req["method"] == "resources/unsubscribe"
    assert req["params"]["uri"] == "schema://bar"


def test_mcp_client_extended_requests():
    """Test test_mcp_client_extended_requests."""
    client = MCPClient()
    req1 = client.build_list_prompts_request("curs1")
    assert req1["method"] == "prompts/list"
    assert req1["params"]["cursor"] == "curs1"

    req1_nocur = client.build_list_prompts_request()
    assert req1_nocur["method"] == "prompts/list"
    assert "params" not in req1_nocur or "cursor" not in req1_nocur["params"]

    req2 = client.build_get_prompt_request("my_prompt", {"foo": "bar"})
    assert req2["method"] == "prompts/get"
    assert req2["params"]["name"] == "my_prompt"
    assert req2["params"]["arguments"] == {"foo": "bar"}

    req2_noarg = client.build_get_prompt_request("my_prompt")
    assert req2_noarg["method"] == "prompts/get"
    assert "params" not in req2_noarg or "arguments" not in req2_noarg["params"]

    req3 = client.build_list_resources_request("curs2")
    assert req3["method"] == "resources/list"
    assert req3["params"]["cursor"] == "curs2"

    req3_nocur = client.build_list_resources_request()
    assert req3_nocur["method"] == "resources/list"
    assert "params" not in req3_nocur or "cursor" not in req3_nocur["params"]

    req4 = client.build_read_resource_request("schema://read")
    assert req4["method"] == "resources/read"
    assert req4["params"]["uri"] == "schema://read"

    req5 = client.build_list_tools_request("curs3")
    assert req5["method"] == "tools/list"
    assert req5["params"]["cursor"] == "curs3"

    req5_nocur = client.build_list_tools_request()
    assert req5_nocur["method"] == "tools/list"
    assert "params" not in req5_nocur or "cursor" not in req5_nocur["params"]


def test_mcp_client_pagination():
    """Test test_mcp_client_pagination."""
    client = MCPClient()
    req = client.build_paginated_request("test/paginate", "my_cursor")
    assert req["method"] == "test/paginate"
    assert req["params"]["cursor"] == "my_cursor"

    req_no_cur = client.build_paginated_request("test/paginate")
    assert "params" not in req_no_cur or "cursor" not in req_no_cur["params"]

    res, ncur = client.parse_paginated_result(
        '{"jsonrpc": "2.0", "result": {"items": [], "nextCursor": "next_page"}, "id": 1}'
    )
    assert res["items"] == []
    assert ncur == "next_page"


def test_mcp_client_create_message():
    """Test test_mcp_client_create_message."""
    client = MCPClient()
    req = client.build_create_message_request(
        messages=[{"role": "user", "content": {"type": "text", "text": "hi"}}],
        system_prompt="sys",
        max_tokens=500,
    )
    assert req["method"] == "messages/create"
    assert req["params"]["messages"][0]["content"]["text"] == "hi"
    assert req["params"]["systemPrompt"] == "sys"
    assert req["params"]["maxTokens"] == 500

    req2 = client.build_create_message_request(messages=[])
    assert "systemPrompt" not in req2["params"]

    res = client.parse_create_message_result(
        '{"jsonrpc": "2.0", "result": {"content": "response"}, "id": 1}'
    )
    assert res["content"] == "response"


def test_mcp_client_misc_requests():
    """Test test_mcp_client_misc_requests."""
    client = MCPClient()
    req1 = client.build_complete_request(
        {"type": "ref/resource", "uri": "schema://x"}, {"name": "arg", "value": "x"}
    )
    assert req1["method"] == "completion/complete"
    assert req1["params"]["ref"] == {"type": "ref/resource", "uri": "schema://x"}

    req2 = client.build_list_roots_request()
    assert req2["method"] == "roots/list"

    req3 = client.build_set_level_request("debug")
    assert req3["method"] == "logging/setLevel"
    assert req3["params"]["level"] == "debug"

    req4 = client.build_ping_request()
    assert req4["method"] == "ping"


def test_mcp_client_parse_client_result():
    """Test test_mcp_client_parse_client_result."""
    client = MCPClient()
    res = client.parse_client_result(
        '{"jsonrpc": "2.0", "result": {"foo": "bar"}, "id": 1}'
    )
    assert res == {"foo": "bar"}

    import pytest

    with pytest.raises(RuntimeError) as exc_info:
        client.parse_client_result(
            '{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error"}, "id": 1}'
        )
    assert "MCP JSON-RPC Error -32603: Internal error" in str(exc_info.value)


def test_mcp_client_complete_request_prompt():
    """Test test_mcp_client_complete_request_prompt."""
    client = MCPClient()
    req = client.build_complete_request(
        {"type": "ref/prompt", "name": "foo"}, {"name": "arg", "value": "x"}
    )
    assert req["params"]["ref"]["type"] == "ref/prompt"
    assert req["params"]["ref"]["name"] == "foo"


def test_mcp_client_request_resolution():
    """Test test_mcp_client_request_resolution."""
    client = MCPClient()
    req = client.build_ping_request()

    # Verify tracking
    client.track_request(req)
    assert req["id"] in client._pending_requests
    assert client._pending_requests[req["id"]] == "ping"

    # Verify resolution
    resp = {"jsonrpc": "2.0", "id": req["id"], "result": {}}
    client.resolve_response(resp)

    assert req["id"] not in client._pending_requests
    assert req["id"] in client._resolved_responses
    assert client._resolved_responses[req["id"]] == resp


def test_mcp_client_request_resolution_missing_id():
    """Test test_mcp_client_request_resolution_missing_id."""
    client = MCPClient()

    # Missing ID tracking
    client.track_request({"method": "ping"})
    assert not client._pending_requests

    # Missing ID resolution
    client.resolve_response({"result": {}})
    assert not client._resolved_responses


def test_mcp_client_request_resolution_unknown_id():
    """Test test_mcp_client_request_resolution_unknown_id."""
    client = MCPClient()

    # Unknown ID resolution
    client.resolve_response({"id": 999, "result": {}})
    assert 999 not in client._resolved_responses


def test_classes_emit_ref():
    """Test test_classes_emit_ref."""
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        components={
            "schemas": {
                "MyClass": Schema(
                    type="object",
                    properties={
                        "my_ref": Reference(**{"$ref": "#/components/schemas/Other"})
                    },
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
    from openapi_client.mcp import execute_tool, get_resources, get_tools, read_resource

    assert len(get_tools()) == 5
    assert len(get_resources()) == 1
    assert read_resource("schema://current")["openapi"] == "3.0.0"

    from openapi_client import sdk

    # Just mock the sdk functions temporarily
    old_to = getattr(sdk, "generate_to_openapi", None)
    old_from = getattr(sdk, "generate_from_openapi", None)
    old_docs = getattr(sdk, "generate_docs_json", None)

    sdk.generate_to_openapi = lambda **kwargs: "to"
    sdk.generate_from_openapi = lambda **kwargs: "from"
    sdk.generate_docs_json = lambda **kwargs: "docs"

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
            sdk.generate_to_openapi = old_to
        if old_from:
            sdk.generate_from_openapi = old_from
        if old_docs:
            sdk.generate_docs_json = old_docs


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


def test_from_openapi() -> None:
    """Test sdk.generate_from_openapi delegates to cli_generate_from_openapi."""
    with patch("openapi_client.sdk.cli_generate_from_openapi") as mock_fn:
        sdk.generate_from_openapi("input.json", "out_dir")
        mock_fn.assert_called_once()


def test_to_openapi() -> None:
    """Test sdk.generate_to_openapi delegates to cli_generate_to_openapi."""
    with patch("openapi_client.sdk.cli_generate_to_openapi") as mock_fn:
        sdk.generate_to_openapi("input_dir")
        mock_fn.assert_called_once()


def test_to_docs_json() -> None:
    """Test sdk.generate_docs_json delegates to cli_generate_docs_json."""
    with patch("openapi_client.sdk.cli_generate_docs_json") as mock_fn:
        sdk.generate_docs_json("input.json")
        mock_fn.assert_called_once()


def test_serve_json_rpc() -> None:
    """Test sdk.serve_json_rpc delegates to cli_serve_json_rpc."""
    with patch("openapi_client.sdk.cli_serve_json_rpc") as mock_fn:
        sdk.serve_json_rpc()
        mock_fn.assert_called_once()


def test_sync() -> None:
    """Test sdk.run_sync delegates to cli_sync_dir."""
    with patch("openapi_client.sdk.cli_sync_dir") as mock_fn:
        sdk.run_sync("input_dir")
        mock_fn.assert_called_once()


def test_mcp() -> None:
    """Test sdk.mcp delegates to cli_run_mcp_server."""
    with patch("openapi_client.sdk.cli_run_mcp_server") as mock_fn:
        sdk.mcp()
        mock_fn.assert_called_once()


def test_sdk_end_to_end_roundtrip(tmp_path: Path) -> None:
    """Test end-to-end SDK generation and OpenAPI extraction on a temporary project."""
    spec_file = tmp_path / "openapi.json"
    spec_file.write_text(
        json.dumps(
            {
                "openapi": "3.2.0",
                "info": {"title": "SDK E2E", "version": "1.0.0"},
                "paths": {
                    "/items": {
                        "get": {
                            "operationId": "list_items",
                            "responses": {"200": {"description": "ok"}},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "generated"
    sdk.generate_from_openapi(str(spec_file), str(out_dir))
    assert (out_dir / "src" / "client.py").exists()

    out_spec = tmp_path / "extracted.json"
    sdk.generate_to_openapi(str(out_dir / "src" / "client.py"), str(out_spec))
    extracted = json.loads(out_spec.read_text(encoding="utf-8"))
    assert "/items" in extracted["paths"]
