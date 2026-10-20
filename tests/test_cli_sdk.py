"""Tests for CLI SDK emission, cli_sdk_cdd, MCP server/SSE/adapter, and CLI AST parsing."""

from __future__ import annotations

import libcst as cst

from openapi_client.cli_sdk.emit import emit_cli_sdk
from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server
from openapi_client.cli_sdk.parse import extract_cli_from_ast
from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk as emit_cli_sdk_cdd_fn
from openapi_client.models import (
    Components,
    Info,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Schema,
)


def test_emit_cli_sdk_with_servers() -> None:
    """Test test_emit_cli_sdk_with_servers."""
    from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk as emit_cli_sdk_cdd
    from openapi_client.models import Server

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test CLI API", version="1.0.0"),
        servers=[Server(url="https://api.example.com")],
        paths={},
        components=Components(schemas={}),
    )

    code = emit_cli_sdk_cdd(spec)
    assert 'os.environ.get("API_BASE_URL", "https://api.example.com")' in code


def test_emit_cli_sdk() -> None:
    """Test test_emit_cli_sdk."""
    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test CLI API", version="1.0.0"),
        paths={
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
        components=Components(schemas={}),
    )

    code = emit_cli_sdk(spec)
    assert "add_parser" in code
    assert "get_test" in code
    assert "add_argument" in code
    assert "--param1" in code


def test_emit_mcp_server() -> None:
    """Test test_emit_mcp_server."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test MCP API", version="1.0.0"),
        paths={
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
        components=Components(schemas={}),
    )

    code = emit_mcp_server(spec)
    assert "start_mcp_server" in code
    assert "get_test" in code
    assert "Test MCP API" in code

    # Try compiling it to ensure it's valid syntax
    compile(code, "mcp_server.py", "exec")


def test_emit_mcp_sse_server() -> None:
    """Test test_emit_mcp_sse_server."""
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test MCP SSE API", version="1.0.0"),
        paths={
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
        components=Components(schemas={}),
    )

    code = emit_mcp_sse_server(spec)
    assert "start_mcp_sse_server" in code
    assert "get_test" in code
    assert "MCPSSEServer" in code

    # Try compiling it to ensure it's valid syntax
    compile(code, "mcp_sse_server.py", "exec")


def test_extract_cli_from_ast() -> None:
    """Test test_extract_cli_from_ast."""
    code = """
import argparse

parser = argparse.ArgumentParser(description="Test CLI API CLI")
subparsers = parser.add_subparsers(dest="command")
get_test_parser = subparsers.add_parser("get_test", help="A test operation updated")
get_test_parser.add_argument("--param1", type=str, help="test param updated", required=True)
"""
    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test CLI API", version="1.0.0"),
        paths={
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
        components=Components(schemas={}),
    )
    mod = cst.parse_module(code)
    extract_cli_from_ast(mod, spec)

    assert spec.paths is not None
    op_test = spec.paths["/test"].get
    assert op_test is not None
    assert op_test.summary == "A test operation updated"
    assert op_test.parameters is not None
    assert op_test.parameters[0].description == "test param updated"


def test_emit_mcp_server_lists() -> None:
    """Test test_emit_mcp_server_lists."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test", version="1.0"),
        paths={
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
        components=Components(schemas={}),
    )
    code = emit_mcp_server(spec)
    assert '"type": "string"' in code


def test_emit_mcp_sse_server_lists() -> None:
    """Test test_emit_mcp_sse_server_lists."""
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test", version="1.0"),
        paths={
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
        components=Components(schemas={}),
    )
    code = emit_mcp_sse_server(spec)
    assert '"type": "string"' in code


def test_emit_mcp_adapter() -> None:
    """Test test_emit_mcp_adapter."""
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test", version="1.0"),
        paths={
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
        components=Components(schemas={}),
    )
    code = emit_mcp_adapter(spec)
    assert "class MCPAdapter" in code
    assert '"type": "number"' in code


def test_emit_mcp_adapter_no_paths() -> None:
    """Test test_emit_mcp_adapter_no_paths."""
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Test", version="1.0"),
        paths=None,
        components=Components(schemas={}),
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
    assert "tools = json.loads('[]')" in c1
    assert "self._tools = json.loads('[]')" in c2
    assert "tools = json.loads('[]')" in c3
    compile(c1, "<mcp_server>", "exec")
    compile(c2, "<mcp_adapter>", "exec")
    compile(c3, "<mcp_sse_server>", "exec")


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
    assert "tools = json.loads('[]')" in c1
    assert "self._tools = json.loads('[]')" in c2
    assert "tools = json.loads('[]')" in c3
    compile(c1, "<mcp_server>", "exec")
    compile(c2, "<mcp_adapter>", "exec")
    compile(c3, "<mcp_sse_server>", "exec")


def test_emit_mcp_param_no_schema() -> None:
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
    assert spec.paths is not None
    op1 = spec.paths["/test1"].get
    assert op1 is not None
    assert op1.parameters is not None
    assert op1.parameters[0].description is None

    code2 = """
parser.add_parser("not_found")
parser.add_parser("test1", help="desc")
parser.add_argument("--other", help="desc")
parser.add_argument("--myarg", help="desc")
"""
    module2 = cst.parse_module(code2)
    extract_cli_from_ast(module2, spec)
    assert op1.summary == "desc"
    assert op1.parameters[0].description == "desc"

    code3 = """
parser.add_parser("test2")
parser.add_argument("--noparams", help="desc")
"""
    spec.paths["/test2"] = PathItem(
        get=Operation(operationId="test2", responses={}, parameters=[])
    )
    module3 = cst.parse_module(code3)
    extract_cli_from_ast(module3, spec)
    op2 = spec.paths["/test2"].get
    assert op2 is not None
    assert op2.parameters == []


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
    assert spec.paths is not None
    op1 = spec.paths["/test1"].get
    assert op1 is not None
    assert op1.operationId == "test1"


def test_cli_sdk_cdd_emit_branches() -> None:
    """Test emit_cli_sdk and emit_cli_sdk_cdd with requestBody, typed schemas, and standalone AST extraction."""
    from openapi_client.models import MediaType, RequestBody

    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0.0"})

    spec.paths = {
        "/test1": PathItem(
            get=Operation(operationId="test1", responses={}, parameters=[])
        ),
        "/test2": PathItem(
            post=Operation(
                operationId="post_test2",
                responses={},
                parameters=[
                    Parameter(name="param1", **{"in": "query", "schema_": None})
                ],
                requestBody=RequestBody(
                    description="Payload",
                    required=True,
                    content={
                        "application/json": MediaType(schema=Schema(type="object"))
                    },
                ),
            )
        ),
        "/test3": PathItem(
            put=Operation(
                operationId="test3",
                responses={},
                parameters=[
                    Parameter(
                        name="param2",
                        **{
                            "in": "query",
                            "schema_": Schema(type="array", ref=None),
                        },
                    )
                ],
                requestBody=RequestBody(
                    required=False,
                    content={
                        "application/json": MediaType(schema=Schema(type="object"))
                    },
                ),
            )
        ),
    }

    code_libcst = emit_cli_sdk(spec)
    assert '"--body"' in code_libcst
    assert 'os.environ.get("API_BASE_URL"' in code_libcst

    code = emit_cli_sdk_cdd_fn(spec)
    assert "def set_cli_args_test1" in code
    assert "def set_cli_args_post_test2" in code
    assert "def set_cli_args_test3" in code
    extract_cli_from_ast(cst.parse_module(code), spec)

    # Test standalone CLI extraction when spec.paths starts as None
    standalone_code = """
import argparse, json
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")
mcp_p = subparsers.add_parser("mcp", help="MCP")
p1 = subparsers.add_parser("get_pets", help="List pets")
p1.add_argument("--limit", type=int, help="Max pets", required=True)
p1.add_argument("--verbose", action="store_true", help="Verbose flag")
p1.add_argument("--tags", action="append", help="Tag list")
p2 = subparsers.add_parser("custom_op", help="Custom op")
p2.add_argument("--body", type=json.loads, help="Body JSON", required=True)
"""
    standalone_spec = OpenAPI(
        openapi="3.2.0", info={"title": "Standalone", "version": "1.0.0"}, paths=None
    )
    from openapi_client.cli_sdk.parse import CLIExtractor

    extractor = CLIExtractor(standalone_spec)
    cst.parse_module(standalone_code).visit(extractor)
    assert standalone_spec.paths is not None
    assert "/pets" in standalone_spec.paths
    pets_op = standalone_spec.paths["/pets"].get
    assert pets_op is not None
    assert pets_op.operationId == "get_pets"
    assert pets_op.summary == "List pets"
    assert pets_op.parameters is not None
    assert len(pets_op.parameters) == 3

    assert "/custom_op" in standalone_spec.paths
    custom_op = standalone_spec.paths["/custom_op"].get
    assert custom_op is not None
    assert custom_op.requestBody is not None

    # Cover current_op.parameters = None branch in standalone mode
    custom_op.parameters = None
    extractor.current_op = custom_op
    cst.parse_module('p2.add_argument("--extra", type=str, help="Extra")').visit(
        extractor
    )
    assert custom_op.parameters is not None
    assert len(custom_op.parameters) == 1
