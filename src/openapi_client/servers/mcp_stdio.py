"""Model Context Protocol (MCP) stdio server for the CDD generator."""

from __future__ import annotations

import contextlib
import json
import sys
from io import StringIO
from typing import Any

from openapi_client import cli as _cli
from openapi_client import mcp as mcp_module


def run_mcp_server() -> None:
    """Run the generator as an MCP server over stdio."""
    nl = chr(10)

    def send_response(
        req_id: Any,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Send a JSON-RPC response over stdout.

        Args:
            req_id: The JSON-RPC request identifier.
            result: Optional result payload dictionary.
            error: Optional error payload dictionary.
        """
        resp: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        sys.stdout.write(json.dumps(resp) + nl)
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id")

            if method == "initialize":
                send_response(
                    req_id,
                    result={
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                        "serverInfo": {
                            "name": "cdd-generator",
                            "version": _cli.get_version(),
                        },
                    },
                )
            elif method in (
                "notifications/initialized",
                "notifications/cancelled",
                "notifications/progress",
            ):
                pass
            elif method == "close":
                send_response(req_id, result={})
                break
            elif method == "ping":
                send_response(req_id, result={})
            elif method == "resources/list":
                send_response(
                    req_id,
                    result={
                        "resources": mcp_module.get_resources(),
                        "nextCursor": None,
                    },
                )
            elif method == "resources/read":
                uri = params.get("uri")
                try:
                    res_data = mcp_module.read_resource(str(uri or ""))
                    send_response(
                        req_id,
                        result={
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "application/json",
                                    "text": json.dumps(res_data),
                                }
                            ]
                        },
                    )
                except ValueError:
                    send_response(
                        req_id, error={"code": -32602, "message": "Resource not found"}
                    )
            elif method == "prompts/list":
                send_response(
                    req_id,
                    result={
                        "prompts": mcp_module.get_prompts(),
                        "nextCursor": None,
                    },
                )
            elif method == "prompts/get":
                prompt_name = str(params.get("name", ""))
                prompt_args = params.get("arguments")
                try:
                    prompt_data = mcp_module.get_prompt(prompt_name, prompt_args)
                    send_response(req_id, result=prompt_data)
                except ValueError:
                    send_response(
                        req_id, error={"code": -32602, "message": "Prompt not found"}
                    )
            elif method == "tools/list":
                send_response(
                    req_id,
                    result={
                        "tools": mcp_module.get_tools(),
                        "nextCursor": None,
                    },
                )
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})

                buffer = StringIO()

                try:
                    with contextlib.redirect_stdout(buffer):
                        if tool_name == "to_openapi":
                            _cli.generate_to_openapi(
                                args.get("input_dir") or args.get("input_path"),
                                args.get("output_path"),
                            )
                        elif tool_name == "from_openapi":
                            _cli.generate_from_openapi(
                                args.get("subcommand", "to_sdk"),
                                args.get("input_path"),
                                None,
                                args.get("output_dir", "."),
                            )
                        elif tool_name == "to_arazzo":
                            _cli.generate_to_arazzo(
                                args.get("input_dir") or args.get("input_path"),
                                args.get("output_path", "arazzo.json"),
                            )
                        elif tool_name == "from_arazzo":
                            _cli.generate_from_arazzo(
                                args.get("subcommand", "to_sdk"),
                                args.get("input_path"),
                                None,
                                args.get("output_dir", "."),
                            )
                        elif tool_name == "sync_dir":
                            _cli.sync_dir(args.get("project_dir"))
                        elif tool_name == "to_docs_json":
                            _cli.generate_docs_json(
                                args.get("input_path"),
                                bool(args.get("no_imports", False)),
                                bool(args.get("no_wrapping", False)),
                                args.get("output_path") or args.get("output_file"),
                            )
                        else:
                            send_response(
                                req_id,
                                error={"code": -32601, "message": "Tool not found"},
                            )
                            continue

                    send_response(
                        req_id,
                        result={
                            "content": [{"type": "text", "text": buffer.getvalue()}]
                        },
                    )
                except Exception as e:  # noqa: BLE001
                    send_response(
                        req_id,
                        result={
                            "content": [{"type": "text", "text": str(e)}],
                            "isError": True,
                        },
                    )
            else:
                if req_id is not None:
                    send_response(
                        req_id, error={"code": -32601, "message": "Method not found"}
                    )
        except Exception as e:  # noqa: BLE001
            if "req_id" in locals() and req_id is not None:
                send_response(req_id, error={"code": -32603, "message": str(e)})
