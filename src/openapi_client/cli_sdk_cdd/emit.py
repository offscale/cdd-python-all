"""Generate a CLI script from an OpenAPI spec using cdd-python."""

from __future__ import annotations

import ast
from collections import OrderedDict
from typing import Any

import libcst as cst
from cdd.emit.argparse_function import argparse_function

from openapi_client.cli_sdk.emit import extract_cli_operations
from openapi_client.functions.utils import get_default_server_url
from openapi_client.models import OpenAPI


def emit_cli_sdk(spec: OpenAPI) -> str:
    """Generate the Python source code string for a CLI application.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated CLI application Python source code.
    """
    body = [
        "import argparse",
        "import json",
        "from json import loads",
        "import os",
        "import sys",
        "from client import Client",
        "",
    ]

    operations: list[tuple[str, str]] = []

    for op_id, desc, params_meta, body_meta in extract_cli_operations(spec):
        params: OrderedDict[str, dict[str, Any]] = OrderedDict()
        ir: dict[str, Any] = {
            "name": op_id,
            "type": "static",
            "doc": desc,
            "params": params,
            "returns": None,
        }

        for p_info in params_meta:
            params[p_info["name"]] = {
                "typ": p_info["py_type"],
                "doc": p_info["description"],
                "default": None if p_info["required"] else "None",
            }

        if body_meta is not None:
            params["body"] = {
                "typ": "dict",
                "doc": body_meta["description"],
                "default": None if body_meta["required"] else "None",
            }

        arg_ast = argparse_function(ir, function_name="set_cli_args_" + op_id)
        code = ast.unparse(arg_ast)
        body.append(code)
        body.append("")
        operations.append((op_id, desc))

    body.append("def main():")
    body.append(
        '    parser = argparse.ArgumentParser(description="Generated Client SDK CLI")'
    )
    body.append('    subparsers = parser.add_subparsers(dest="command")')
    body.append(
        '    mcp_parser = subparsers.add_parser("mcp", help="Start the Model Context Protocol (MCP) server")'
    )
    body.append(
        '    mcp_sse_parser = subparsers.add_parser("mcp_sse", help="Start the Model Context Protocol (MCP) SSE server")'
    )

    for op_id, desc in operations:
        body.append(
            f"    {op_id}_parser = subparsers.add_parser({op_id!r}, help={desc!r})"
        )
        body.append(f"    set_cli_args_{op_id}({op_id}_parser)")

    body.append("")
    body.append("    args = parser.parse_args()")
    default_url = get_default_server_url(spec, fallback="http://localhost:8080/v2")
    body.append(
        f'    c = Client(base_url=os.environ.get("API_BASE_URL", "{default_url}"))'
    )
    body.append("    if not args.command:")
    body.append("        parser.print_help()")
    body.append("        sys.exit(0)")
    body.append("")
    body.append('    if args.command == "mcp":')
    body.append("        from mcp_server import start_mcp_server")
    body.append("        start_mcp_server(c)")
    body.append("        sys.exit(0)")
    body.append("")
    body.append('    if args.command == "mcp_sse":')
    body.append("        from mcp_sse_server import start_mcp_sse_server")
    body.append("        start_mcp_sse_server(c)")
    body.append("        sys.exit(0)")
    body.append("")
    body.append("    method = getattr(c, args.command)")
    body.append("    kwargs = vars(args).copy()")
    body.append("    kwargs.pop('command')")
    body.append("    print(method(**kwargs))")
    body.append("")
    body.append('if __name__ == "__main__":')
    body.append("    main()")
    body.append("")

    return cst.parse_module("\n".join(body)).code
