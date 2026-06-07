"""Tests for test_mcp_client.py."""

from openapi_client.mcp_client.client import MCPClient


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
