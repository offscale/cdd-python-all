"""Tests for CLI SDK emission, cli_sdk_cdd, MCP server/SSE/adapter, and CLI AST parsing."""

from __future__ import annotations

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
from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server
from openapi_client.models import PathItem, Schema
from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk as emit_cli_sdk_cdd_fn


def test_emit_cli_sdk_with_servers():
    """Test test_emit_cli_sdk_with_servers."""
    from openapi_client.models import Server
    from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk as emit_cli_sdk_cdd

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Test CLI API", version="1.0.0"),
            "servers": [Server(url="https://api.example.com")],
            "paths": {},
            "components": Components(schemas={}),
        }
    )

    code = emit_cli_sdk_cdd(spec)
    assert 'os.environ.get("API_BASE_URL", "https://api.example.com")' in code


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


def test_emit_mcp_schema_missing_type() -> None:
    """Test emit MCP server when schema has no type."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={
            "/test": PathItem.model_construct(
                get=Operation.model_construct(
                    parameters=[
                        Parameter.model_construct(
                            name="p1", in_="query", schema_=Schema.model_construct()
                        )
                    ]
                )
            )
        },
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)
    assert '"type": null' in c1
    assert '"type": null' in c2
    assert '"type": null' in c3


def test_emit_mcp_methods() -> None:
    """Test emit MCP server with all HTTP methods."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={
            "/test": PathItem.model_construct(
                post=Operation.model_construct(operationId="post_test"),
                put=Operation.model_construct(operationId="put_test"),
                delete=Operation.model_construct(operationId="delete_test"),
                patch=Operation.model_construct(operationId="patch_test"),
            )
        },
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)

    for code in (c1, c2, c3):
        assert "post_test" in code
        assert "put_test" in code
        assert "delete_test" in code
        assert "patch_test" in code


def test_emit_mcp_schema_missing_paths() -> None:
    """Test emit MCP server when spec has no paths."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0", info=Info.model_construct(title="API", version="1"), paths=None
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)
    assert "tools = []" in c1
    assert "self._tools = []" in c2
    assert "tools = []" in c3


def test_emit_mcp_schema_no_parameters() -> None:
    """Test emit MCP server when operation has no parameters."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={
            "/test": PathItem.model_construct(
                get=Operation.model_construct(parameters=None)
            )
        },
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)
    assert '"required": []' in c1
    assert '"required": []' in c2
    assert '"required": []' in c3


def test_emit_mcp_schema_list_type() -> None:
    """Test emit MCP server when schema type is a list."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={
            "/test": PathItem.model_construct(
                get=Operation.model_construct(
                    parameters=[
                        Parameter.model_construct(
                            name="p1",
                            in_="query",
                            schema_=Schema.model_construct(type=["integer", "null"]),
                        )
                    ]
                )
            )
        },
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)
    assert '"type": "number"' in c1
    assert '"type": "number"' in c2
    assert '"type": "number"' in c3


def test_emit_mcp_schema_false_req() -> None:
    """Test emit MCP server when parameter required is False."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={
            "/test": PathItem.model_construct(
                get=Operation.model_construct(
                    parameters=[
                        Parameter.model_construct(
                            name="p1",
                            in_="query",
                            required=False,
                            schema_=Schema.model_construct(type="string"),
                        )
                    ]
                )
            )
        },
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)
    assert '"required": []' in c1
    assert '"required": []' in c2
    assert '"required": []' in c3


def test_emit_mcp_missing_method() -> None:
    """Test emit MCP server when path item has no HTTP operations."""
    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={"/test": PathItem.model_construct(summary="Test path")},
    )

    c1 = emit_mcp_server(spec)
    c2 = emit_mcp_adapter(spec)
    c3 = emit_mcp_sse_server(spec)
    assert "tools = []" in c1
    assert "self._tools = []" in c2
    assert "tools = []" in c3


def test_emit_mcp_param_no_schema():
    """Test emit MCP server param with no schema explicit."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={
            "/test": PathItem.model_construct(
                get=Operation.model_construct(
                    parameters=[
                        Parameter.model_construct(name="p1", in_="query", schema_=None)
                    ]
                )
            )
        },
    )

    c1 = emit_mcp_server(spec)
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert '"type": "string"' in c1


def test_cli_sdk_parse_branches() -> None:
    """Test extract_cli_from_ast on non-string and positional arguments."""
    code = """
parser.add_parser(var)
parser.add_argument(var)
parser.add_argument("positional", help="desc")
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})

    spec.paths = {
        "/test1": PathItem(
            get=Operation(
                operationId="test1",
                responses={},
                parameters=[Parameter(name="myarg", **{"in": "query"})],
            )
        )
    }
    extract_cli_from_ast(module, spec)
    assert spec.paths["/test1"].get.parameters[0].description is None

    code2 = """
parser.add_parser("not_found")
parser.add_parser("test1", help="desc")
parser.add_argument("--other", help="desc")
parser.add_argument("--myarg", help="desc")
"""
    module2 = cst.parse_module(code2)
    extract_cli_from_ast(module2, spec)
    assert spec.paths["/test1"].get.summary == "desc"
    assert spec.paths["/test1"].get.parameters[0].description == "desc"

    code3 = """
parser.add_parser("test2")
parser.add_argument("--noparams", help="desc")
"""
    spec.paths["/test2"] = PathItem(
        get=Operation(operationId="test2", responses={}, parameters=[])
    )
    module3 = cst.parse_module(code3)
    extract_cli_from_ast(module3, spec)
    assert spec.paths["/test2"].get.parameters == []


def test_cli_sdk_parse_branches_58_exit() -> None:
    """Test extract_cli_from_ast when add_argument has a positional argument."""
    code = """
parser.add_parser("test1")
parser.add_argument("positional", help="desc")
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    spec.paths = {
        "/test1": PathItem(
            get=Operation(operationId="test1", responses={}, parameters=[])
        )
    }
    extract_cli_from_ast(module, spec)
    assert spec.paths["/test1"].get.operationId == "test1"


def test_cli_sdk_cdd_emit_branches() -> None:
    """Test emit_cli_sdk with empty parameters, None schema, and typed schema."""
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})

    spec.paths = {
        "/test1": PathItem(
            get=Operation(operationId="test1", responses={}, parameters=[])
        ),
        "/test2": PathItem(
            get=Operation(
                operationId="test2",
                responses={},
                parameters=[
                    Parameter(name="param1", **{"in": "query", "schema_": None})
                ],
            )
        ),
        "/test3": PathItem(
            get=Operation(
                operationId="test3",
                responses={},
                parameters=[
                    Parameter(
                        name="param2",
                        **{
                            "in": "query",
                            "schema_": Schema(type="integer", **{"ref": None}),
                        },
                    )
                ],
            )
        ),
    }

    code = emit_cli_sdk_cdd_fn(spec)
    assert "def set_cli_args_test1" in code
    assert "def set_cli_args_test2" in code
    assert "def set_cli_args_test3" in code
