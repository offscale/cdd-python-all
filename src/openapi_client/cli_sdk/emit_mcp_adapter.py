"""Generates a Model Context Protocol (MCP) adapter for programmatic SDK integration."""

from __future__ import annotations

import json

from openapi_client.cli_sdk.emit_mcp import extract_mcp_tools_from_spec
from openapi_client.models import OpenAPI


def emit_mcp_adapter(spec: OpenAPI) -> str:
    """Emit the `mcp_adapter.py` source code.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated Python source code for `mcp_adapter.py`.
    """
    tools = extract_mcp_tools_from_spec(spec)
    tools_json = json.dumps(tools, indent=4)
    title = spec.info.title if spec.info else "API"
    version = spec.info.version if spec.info else "1.0.0"

    code = f'''"""Native MCP adapter for programmatic SDK integration."""

import json

class MCPAdapter:
    """Adapter to expose SDK methods as MCP tools and resources."""

    def __init__(self, client):
        self.client = client
        self._tools = json.loads({tools_json!r})

    def get_tools(self):
        """Return the available SDK methods mapped to the MCP tool schema."""
        return self._tools

    def execute_tool(self, name: str, arguments: dict):
        """Execute a tool locally using the SDK methods."""
        if hasattr(self.client, name):
            func = getattr(self.client, name)
            return func(**arguments)
        raise ValueError(f"Unknown tool: {{name}}")

    def get_resources(self):
        """Return the available SDK internal resources mapped to the MCP schema."""
        return [
            {{
                "uri": "schema://current",
                "name": "Current internal OpenAPI specification",
                "mimeType": "application/json",
            }}
        ]

    def read_resource(self, uri: str):
        """Read a specific resource locally using SDK methods."""
        if uri == "schema://current":
            return {{"openapi": {spec.openapi!r}, "info": {{"title": {title!r}, "version": {version!r}}}}}
        raise ValueError(f"Resource not found: {{uri}}")
'''
    return code
