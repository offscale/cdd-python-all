"""Generate a CLI script from an OpenAPI spec using cdd-python."""

from __future__ import annotations

import ast
from collections import OrderedDict

from cdd.emit.argparse_function import argparse_function

from openapi_client.functions.utils import (
    get_default_server_url,
    map_openapi_type_to_python,
    sanitize_name,
)
from openapi_client.models import OpenAPI


def emit_cli_sdk(spec: OpenAPI) -> str:
    """Generate the Python source code string for a CLI application.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated CLI application Python source code.
    """
    body = ["import argparse", "import sys", "from client import Client", ""]

    operations: list[tuple[str, str]] = []

    if spec.paths:
        for path, path_item in spec.paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    raw_op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    op_id = sanitize_name(raw_op_id)
                    desc = operation.summary or f"{method.upper()} {path}"

                    ir = {
                        "name": op_id,
                        "type": "static",
                        "doc": desc,
                        "params": OrderedDict(),
                        "returns": None,
                    }

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

                            ir["params"][p_name] = {
                                "typ": map_openapi_type_to_python(str(p_type)),
                                "doc": p_desc,
                                "default": None if req else "None",
                            }

                    arg_ast = argparse_function(
                        ir, function_name="set_cli_args_" + op_id
                    )
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
    body.append("    import os")
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

    return "\n".join(body)
