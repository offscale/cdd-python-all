"""JSON-RPC 2.0 HTTP server exposing CDD CLI subcommands."""

from __future__ import annotations

import http.server
import json
import traceback
from typing import Any

from openapi_client import cli as _cli


class JSONRPCRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handler for incoming HTTP JSON-RPC 2.0 requests."""

    def do_POST(self) -> None:
        """Handle POST requests for JSON-RPC."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except ValueError:
            self.send_error(400, "Bad Request: Invalid JSON")
            return

        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            self.send_error(400, "Bad Request: Invalid JSON-RPC")
            return

        method = request.get("method")
        params = request.get("params", {})
        req_id = request.get("id")

        result: Any = None
        error: dict[str, Any] | None = None

        try:
            if method == "to_openapi":
                _cli.generate_to_openapi(params.get("input"), params.get("output"))
                result = "Success"
            elif method in (
                "from_openapi_to_sdk",
                "from_openapi_to_sdk_cli",
                "from_openapi_to_server",
            ):
                subcommand = method.replace("from_openapi_", "")
                _cli.generate_from_openapi(
                    subcommand,
                    params.get("input"),
                    params.get("input_dir"),
                    params.get("output"),
                    params.get("no_github_actions", False),
                    params.get("no_installable_package", False),
                    params.get("tests", False),
                )
                result = "Success"
            elif method == "to_arazzo":
                _cli.generate_to_arazzo(params.get("input"), params.get("output"))
                result = "Success"
            elif method in (
                "from_arazzo_to_sdk",
                "from_arazzo_to_sdk_cli",
                "from_arazzo_to_server",
                "from_arazzo_to_tests",
            ):
                subcommand = method.replace("from_arazzo_", "")
                _cli.generate_from_arazzo(
                    subcommand,
                    params.get("input"),
                    params.get("input_dir"),
                    params.get("output", "."),
                    params.get("no_github_actions", False),
                    params.get("no_installable_package", False),
                    params.get("tests", False),
                )
                result = "Success"
            elif method == "to_docs_json":
                _cli.generate_docs_json(
                    params.get("input"),
                    params.get("no_imports", False),
                    params.get("no_wrapping", False),
                    params.get("output"),
                )
                result = "Success"
            elif method == "sync":
                _cli.sync_dir(params.get("dir"))
                result = "Success"
            else:
                error = {"code": -32601, "message": "Method not found"}
        except Exception as e:  # noqa: BLE001
            error = {
                "code": -32000,
                "message": str(e),
                "data": traceback.format_exc(),
            }

        response: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id}
        if error:
            response["error"] = error
        else:
            response["result"] = result

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))


def serve_json_rpc(port: int, listen: str = "127.0.0.1") -> None:
    """Run a JSON-RPC 2.0 HTTP server exposing the CLI subcommands.

    Args:
        port: TCP port to listen on.
        listen: Host address to bind to (defaults to `'127.0.0.1'`).
    """
    server_address = (listen, port)
    httpd = http.server.HTTPServer(server_address, JSONRPCRequestHandler)
    print(f"Starting JSON-RPC server on {listen}:{port}")
    httpd.serve_forever()
