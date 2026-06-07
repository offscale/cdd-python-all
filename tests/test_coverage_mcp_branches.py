"""Tests for mcp branch coverage."""

from openapi_client.models import OpenAPI, Info, Operation, Parameter, Schema, PathItem


def test_emit_mcp_schema_missing_type():
    """Test emit MCP server when schema has no type."""
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
                        Parameter.model_construct(
                            name="p1", in_="query", schema_=Schema.model_construct()
                        )
                    ]
                )
            )
        },
    )

    c1 = emit_mcp_server(spec)
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert '"type": null' in c1


"""Tests for mcp branch coverage."""


"""Tests for mcp branch coverage."""


def test_emit_mcp_methods():
    """Test emit MCP server with all methods."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

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
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)

    assert "post_test" in c1
    assert "put_test" in c1
    assert "delete_test" in c1
    assert "patch_test" in c1


def test_emit_mcp_schema_missing_paths():
    """Test emit MCP server when no paths."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI.model_construct(
        openapi="3.0.0", info=Info.model_construct(title="API", version="1"), paths=None
    )

    c1 = emit_mcp_server(spec)
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert "tools = []" in c1


def test_emit_mcp_schema_no_parameters():
    """Test emit MCP server when no parameters."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

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
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert '"required": []' in c1


def test_emit_mcp_schema_list_type():
    """Test emit MCP server when schema type is a list."""
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
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert '"type": "number"' in c1


def test_emit_mcp_schema_false_req():
    """Test emit MCP server when required is false."""
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
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert '"required": []' in c1


"""Tests for mcp branch coverage."""


def test_emit_mcp_missing_method():
    """Test emit MCP server when path has no get method but has paths."""
    from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
    from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
    from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server

    spec = OpenAPI.model_construct(
        openapi="3.0.0",
        info=Info.model_construct(title="API", version="1"),
        paths={"/test": PathItem.model_construct(summary="Test path")},
    )

    c1 = emit_mcp_server(spec)
    emit_mcp_adapter(spec)
    emit_mcp_sse_server(spec)
    assert "tools = []" in c1
