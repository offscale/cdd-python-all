"""Tests for test_cli_sdk_extra.py."""

from openapi_client.models import OpenAPI, Info, Components, Operation, Parameter


def test_emit_mcp_server_lists():
    """Test test_emit_mcp_server_lists."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test", version="1.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        parameters=[
                            Parameter(
                                name="param1",
                                **{
                                    "in": "query",
                                    "schema_": {"type": ["string", "null"]},
                                },
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )
    code = emit_mcp_server(spec)
    assert '"type": "string"' in code


def test_emit_mcp_sse_server_lists():
    """Test test_emit_mcp_sse_server_lists."""
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test", version="1.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        parameters=[
                            Parameter(
                                name="param1",
                                **{
                                    "in": "query",
                                    "schema_": {"type": ["string", "null"]},
                                },
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )
    code = emit_mcp_sse_server(spec)
    assert '"type": "string"' in code


def test_emit_mcp_adapter():
    """Test test_emit_mcp_adapter."""
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test", version="1.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        parameters=[
                            Parameter(
                                name="param1",
                                required=True,
                                **{
                                    "in": "query",
                                    "schema_": {"type": ["integer", "null"]},
                                },
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )
    code = emit_mcp_adapter(spec)
    assert "class MCPAdapter" in code
    assert '"type": "number"' in code


def test_emit_mcp_adapter_no_paths():
    """Test test_emit_mcp_adapter_no_paths."""
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test", version="1.0"),
            "paths": None,
            "components": Components(schemas={}),
        }
    )
    code = emit_mcp_adapter(spec)
    assert "class MCPAdapter" in code
