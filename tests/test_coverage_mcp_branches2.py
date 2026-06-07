"""Tests for mcp branch coverage part 2."""

from openapi_client.models import OpenAPI, Info, Operation, Parameter, PathItem


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
