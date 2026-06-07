"""Generates an MCP SSE (Server-Sent Events) HTTP Gateway for a Python SDK."""

import json
from openapi_client.models import OpenAPI


def emit_mcp_sse_server(spec: OpenAPI) -> str:
    """Emit the mcp_sse_server.py source code."""
    title = spec.info.title if spec.info else "API"
    version = spec.info.version if spec.info else "1.0.0"

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
                                    p_type = "number"  # or integer

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

    code = f'''"""Model Context Protocol (MCP) SSE server integration."""

import json
import traceback
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import uuid

class MCPSSEServer(BaseHTTPRequestHandler):
    """HTTP Server handling SSE connections for MCP."""

    # Class-level storage for simplicity in this generated output
    # In a real async framework, this would be attached to app state
    clients = {{}}
    tools = {tools_json}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle incoming SSE connection setup."""
        if self.path == "/mcp/sse":
            session_id = str(uuid.uuid4())

            # Send SSE headers
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Send the endpoint event
            self.wfile.write(b"event: endpoint\\n")
            self.wfile.write(f"data: /mcp/message?session_id={{session_id}}\\n\\n".encode("utf-8"))
            self.wfile.flush()

            # We would normally keep this connection alive and push to self.wfile
            # For a basic BaseHTTPRequestHandler, this is blocking.
            # Real implementations use FastAPI/Starlette for SSE.
            self.wfile.write(b"event: ping\\ndata: {{}}\\n\\n")
            self.wfile.flush()
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        """Handle incoming JSON-RPC messages."""
        if self.path.startswith("/mcp/message"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                req = json.loads(body)
            except ValueError:
                self.send_error(400, "Bad Request: Invalid JSON")
                return

            # Extract HTTP Request/Auth Bridging
            auth_header = self.headers.get("Authorization")
            if auth_header and hasattr(self.server, "client") and self.server.client:
                # Assuming the client can accept an authorization token
                if hasattr(self.server.client, "set_auth_token"):
                    self.server.client.set_auth_token(auth_header)
                elif hasattr(self.server.client, "api_key"):
                    self.server.client.api_key = auth_header

            # For a real implementation, we would route this message to the SSE queue
            # of the specific session_id. Here we will just process and return directly
            # via the HTTP response for testing/demonstration purposes of the object schema.

            # ... handling logic similar to stdio ...
            method = req.get("method")
            params = req.get("params", {{}})
            req_id = req.get("id")

            result = None
            error = None

            if method == "initialize":
                result = {{
                    "protocolVersion": "2024-11-05",
                    "capabilities": {{"tools": {{}}, "resources": {{}}, "prompts": {{}}, "logging": {{}}}},
                    "serverInfo": {{"name": "{title}", "version": "{version}"}}
                }}
            elif method == "notifications/initialized":
                pass
            elif method == "notifications/cancelled":
                # Cancellation of an ongoing request
                pass
            elif method == "notifications/progress":
                # Progress tracking updates
                pass
            elif method == "close":
                # Graceful Disconnect / Close
                result = {{}}
            elif method == "ping":
                result = {{}}
            elif method == "logging/setLevel":
                result = {{}}
            elif method == "resources/list":
                cursor = params.get("cursor")
                result = {{"resources": [], "nextCursor": None}}
            elif method == "resources/read":
                uri = params.get("uri")
                result = {{
                    "contents": [
                        {{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": "{{\\"error\\": \\"Resource not found\\"}}"
                        }}
                    ]
                }}
            elif method == "prompts/list":
                cursor = params.get("cursor")
                result = {{"prompts": [], "nextCursor": None}}
            elif method == "prompts/get":
                name = params.get("name")
                result = {{
                    "description": "Fallback prompt",
                    "messages": [
                        {{
                            "role": "user",
                            "content": {{
                                "type": "text",
                                "text": "Prompt not found"
                            }}
                        }}
                    ]
                }}
            elif method == "tools/list":
                cursor = params.get("cursor")
                result = {{"tools": self.tools, "nextCursor": None}}
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {{}})

                # In this generated adapter, `self.server.client` holds the reference
                client_ref = getattr(self.server, "client", None)
                if client_ref and hasattr(client_ref, tool_name):
                    func = getattr(client_ref, tool_name)
                    try:
                        res = func(**tool_args)
                        result = {{
                            "content": [{{"type": "text", "text": str(res)}}]
                        }}
                    except Exception as e:
                        result = {{
                            "content": [{{"type": "text", "text": str(e)}}],
                            "isError": True
                        }}
                else:
                    error = {{"code": -32601, "message": "Tool not found"}}
            else:
                if req_id is not None:
                    error = {{"code": -32601, "message": "Method not found"}}

            resp = {{"jsonrpc": "2.0", "id": req_id}}
            if error:
                resp["error"] = error
            elif result is not None:
                resp["result"] = result

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if result is not None or error is not None:
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            else:
                self.wfile.write(b"")
        else:
            self.send_error(404, "Not found")

def start_mcp_sse_server(client, port=8080):
    """Run the MCP SSE server."""
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, MCPSSEServer)

    # Attach client logic directly to the server instance for the handlers to access
    httpd.client = client

    print(f"Starting MCP SSE server on port {{port}}...")
    httpd.serve_forever()
'''
    return code
