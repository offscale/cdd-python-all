"""Generates a Model Context Protocol (MCP) adapter for programmatic SDK integration."""

import json
from openapi_client.models import OpenAPI


def emit_mcp_adapter(spec: OpenAPI) -> str:
    """Emit the mcp_adapter.py source code."""
    tools = []
    if spec.paths:
        for path, path_item in spec.paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    from openapi_client.functions.utils import sanitize_name

                    raw_op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    op_id = sanitize_name(raw_op_id)
                    desc = operation.summary or f"{method.upper()} {path}"

                    properties = {}
                    required = []
                    if operation.parameters:
                        for param in operation.parameters:
                            p_name = getattr(param, "name", "param").replace("-", "_")
                            p_desc = getattr(param, "description", "")
                            req = getattr(param, "required", False)
                            p_type = "string"
                            if getattr(param, "schema_", None):
                                p_type = getattr(param.schema_, "type", "string")
                                if isinstance(p_type, list):
                                    p_type = p_type[0]
                                if p_type == "integer":
                                    p_type = "number"

                            properties[p_name] = {"type": p_type, "description": p_desc}
                            if req:
                                required.append(p_name)

                    tools.append(
                        {
                            "name": op_id,
                            "description": desc,
                            "inputSchema": {
                                "type": "object",
                                "properties": properties,
                                "required": required,
                            },
                        }
                    )

    tools_json = json.dumps(tools, indent=4)

    code = f'''"""Native MCP adapter for programmatic SDK integration."""

import json

class MCPAdapter:
    """Adapter to expose SDK methods as MCP tools and resources."""

    def __init__(self, client):
        self.client = client
        self._tools = {tools_json}

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
            return {{"openapi": "3.0.0", "info": {{"title": "API", "version": "1.0.0"}}}}
        raise ValueError(f"Resource not found: {{uri}}")
'''
    return code
