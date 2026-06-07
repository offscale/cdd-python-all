"""Generates a Model Context Protocol (MCP) server for a Python SDK."""

import json
from openapi_client.models import OpenAPI


def emit_mcp_server(spec: OpenAPI) -> str:
    """Emit the mcp_server.py source code."""
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

    code = f'''"""Model Context Protocol (MCP) server integration."""

import sys
import json
import traceback

def start_mcp_server(client):
    """Run the MCP server reading from stdin and writing to stdout."""
    tools = {tools_json}

    def send_response(id, result=None, error=None):
        resp = {{"jsonrpc": "2.0", "id": id}}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            params = req.get("params", {{}})
            req_id = req.get("id")

            if method == "initialize":
                send_response(req_id, result={{
                    "protocolVersion": "2024-11-05",
                    "capabilities": {{"tools": {{}}, "resources": {{}}, "prompts": {{}}, "logging": {{}}}},
                    "serverInfo": {{"name": "{title}", "version": "{version}"}}
                }})
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
                send_response(req_id, result={{}})
                break
            elif method == "ping":
                send_response(req_id, result={{}})
            elif method == "logging/setLevel":
                send_response(req_id, result={{}})
            elif method == "resources/list":
                cursor = params.get("cursor")
                send_response(req_id, result={{
                    "resources": [],
                    "nextCursor": None
                }})
            elif method == "resources/read":
                uri = params.get("uri")
                send_response(req_id, result={{
                    "contents": [
                        {{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": \'{{"error": "Resource not found"}}\'
                        }}
                    ]
                }})
            elif method == "prompts/list":
                cursor = params.get("cursor")
                send_response(req_id, result={{
                    "prompts": [],
                    "nextCursor": None
                }})
            elif method == "prompts/get":
                name = params.get("name")
                send_response(req_id, result={{
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
                }})
            elif method == "tools/list":
                cursor = params.get("cursor")
                send_response(req_id, result={{"tools": tools, "nextCursor": None}})
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {{}})
                if hasattr(client, tool_name):
                    func = getattr(client, tool_name)
                    try:
                        res = func(**tool_args)
                        send_response(req_id, result={{
                            "content": [{{"type": "text", "text": str(res)}}]
                        }})
                    except Exception as e:
                        send_response(req_id, result={{
                            "content": [{{"type": "text", "text": str(e)}}],
                            "isError": True
                        }})
                else:
                    send_response(req_id, error={{"code": -32601, "message": "Tool not found"}})
            else:
                if req_id is not None:
                    send_response(req_id, error={{"code": -32601, "message": "Method not found"}})
        except Exception as e:
            if "req_id" in locals() and req_id is not None:
                send_response(req_id, error={{"code": -32603, "message": str(e)}})
'''
    return code
