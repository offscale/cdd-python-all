"""Generates an MCP SSE (Server-Sent Events) HTTP Gateway for a Python SDK."""

from __future__ import annotations

import json

from openapi_client.cli_sdk.emit_mcp import extract_mcp_tools_from_spec
from openapi_client.models import OpenAPI


def emit_mcp_sse_server(spec: OpenAPI) -> str:
    """Emit the `mcp_sse_server.py` source code.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated Python source code for `mcp_sse_server.py`.
    """
    title = spec.info.title if spec.info else "API"
    version = spec.info.version if spec.info else "1.0.0"

    tools = extract_mcp_tools_from_spec(spec)
    tools_json = json.dumps(tools, indent=4)

    code = f'''"""Model Context Protocol (MCP) SSE server integration."""

import json
import traceback
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import uuid

class MCPSSEServer(BaseHTTPRequestHandler):
    """HTTP Server handling SSE connections for MCP."""

    clients = {{}}
    tools = json.loads({tools_json!r})

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

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            self.wfile.write(b"event: endpoint\\n")
            self.wfile.write(f"data: /mcp/message?session_id={{session_id}}\\n\\n".encode("utf-8"))
            self.wfile.flush()

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

            auth_header = self.headers.get("Authorization")
            if auth_header and hasattr(self.server, "client") and self.server.client:
                if hasattr(self.server.client, "set_auth_token"):
                    self.server.client.set_auth_token(auth_header)
                elif hasattr(self.server.client, "api_key"):
                    self.server.client.api_key = auth_header

            method = req.get("method")
            params = req.get("params", {{}})
            req_id = req.get("id")

            result = None
            error = None

            if method == "initialize":
                result = {{
                    "protocolVersion": "2024-11-05",
                    "capabilities": {{"tools": {{}}, "resources": {{}}, "prompts": {{}}, "logging": {{}}}},
                    "serverInfo": {{"name": {title!r}, "version": {version!r}}}
                }}
            elif method == "notifications/initialized":
                pass
            elif method == "notifications/cancelled":
                pass
            elif method == "notifications/progress":
                pass
            elif method == "close":
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
                            "text": \'{{"error": "Resource not found"}}\'
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

    httpd.client = client

    print(f"Starting MCP SSE server on port {{port}}...")
    httpd.serve_forever()
'''
    return code
