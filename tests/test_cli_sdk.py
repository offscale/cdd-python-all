"""Tests for test_cli_sdk.py."""

import libcst as cst
from openapi_client.models import (
    OpenAPI,
    Info,
    Components,
    Operation,
    Parameter,
)
from openapi_client.cli_sdk.emit import emit_cli_sdk
from openapi_client.cli_sdk.parse import extract_cli_from_ast


def test_emit_cli_sdk():
    """Test test_emit_cli_sdk."""
    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test CLI API", version="1.0.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        summary="A test operation",
                        parameters=[
                            Parameter(
                                name="param1",
                                description="test param",
                                required=True,
                                **{"in": "query"},
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )

    code = emit_cli_sdk(spec)
    assert "add_parser" in code
    assert "get_test" in code
    assert "add_argument" in code
    assert "--param1" in code


def test_emit_mcp_server():
    """Test test_emit_mcp_server."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test MCP API", version="1.0.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        summary="A test operation",
                        parameters=[
                            Parameter(
                                name="param1",
                                description="test param",
                                required=True,
                                **{"in": "query", "schema_": {"type": "integer"}},
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )

    code = emit_mcp_server(spec)
    assert "start_mcp_server" in code
    assert "get_test" in code
    assert "Test MCP API" in code

    # Try compiling it to ensure it's valid syntax
    compile(code, "mcp_server.py", "exec")


def test_emit_mcp_sse_server():
    """Test test_emit_mcp_sse_server."""
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test MCP SSE API", version="1.0.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        summary="A test operation",
                        parameters=[
                            Parameter(
                                name="param1",
                                description="test param",
                                required=True,
                                **{"in": "query", "schema_": {"type": "integer"}},
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )

    code = emit_mcp_sse_server(spec)
    assert "start_mcp_sse_server" in code
    assert "get_test" in code
    assert "MCPSSEServer" in code

    # Try compiling it to ensure it's valid syntax
    compile(code, "mcp_sse_server.py", "exec")


def test_extract_cli_from_ast():
    """Test test_extract_cli_from_ast."""
    code = """
import argparse

parser = argparse.ArgumentParser(description="Test CLI API CLI")
subparsers = parser.add_subparsers(dest="command")
get_test_parser = subparsers.add_parser("get_test", help="A test operation updated")
get_test_parser.add_argument("--param1", type=str, help="test param updated", required=True)
"""
    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test CLI API", version="1.0.0"),
            "paths": {
                "/test": {
                    "get": Operation(
                        operationId="get_test",
                        summary="A test operation",
                        parameters=[
                            Parameter(
                                name="param1",
                                description="test param",
                                required=True,
                                **{"in": "query"},
                            )
                        ],
                    )
                }
            },
            "components": Components(schemas={}),
        }
    )
    mod = cst.parse_module(code)
    extract_cli_from_ast(mod, spec)

    assert getattr(spec.paths["/test"], "get").summary == "A test operation updated"
    assert (
        getattr(spec.paths["/test"], "get").parameters[0].description
        == "test param updated"
    )
