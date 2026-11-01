"""Generates a Model Context Protocol (MCP) adapter for programmatic SDK integration."""

from __future__ import annotations

import json

import libcst as cst

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

from __future__ import annotations

import json
from typing import Any


class MCPAdapter:
    """Adapter to expose SDK methods as MCP tools and resources."""

    def __init__(self, client: Any) -> None:
        """Initialize the MCP adapter with an SDK client instance.

        Args:
            client: The generated SDK `Client` instance.
        """
        self.client = client
        self._tools = json.loads({tools_json!r})

    def get_tools(self) -> list[dict[str, Any]]:
        """Return the available SDK methods mapped to the MCP tool schema.

        Returns:
            List of MCP tool definition dictionaries.
        """
        return self._tools

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool locally using the SDK methods.

        Args:
            name: The MCP tool name corresponding to a client method.
            arguments: Keyword arguments dictionary to pass to the client method.

        Returns:
            The result returned by the invoked SDK client method.

        Raises:
            ValueError: If `name` does not match an available SDK method.
        """
        if hasattr(self.client, name):
            func = getattr(self.client, name)
            return func(**arguments)
        raise ValueError(f"Unknown tool: {{name}}")

    def get_resources(self) -> list[dict[str, str]]:
        """Return the available SDK internal resources mapped to the MCP schema.

        Returns:
            List of MCP resource descriptor dictionaries.
        """
        return [
            {{
                "uri": "schema://current",
                "name": "Current internal OpenAPI specification",
                "mimeType": "application/json",
            }}
        ]

    def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a specific resource locally using SDK methods.

        Args:
            uri: Resource URI to read.

        Returns:
            Dictionary payload of the requested resource.

        Raises:
            ValueError: If `uri` is not a recognized resource.
        """
        if uri == "schema://current":
            return {{"openapi": {spec.openapi!r}, "info": {{"title": {title!r}, "version": {version!r}}}}}
        raise ValueError(f"Resource not found: {{uri}}")
'''
    return cst.parse_module(code).code
