"""Generate a CLI script from an OpenAPI spec using cdd-python."""

import ast
from collections import OrderedDict
from openapi_client.models import OpenAPI
from cdd.emit.argparse_function import argparse_function


def map_openapi_type_to_python(openapi_type: str) -> str:
    """
    Map an OpenAPI type string to the corresponding Python type string.

    :param openapi_type: The OpenAPI type string.
    :type openapi_type: ```str```

    :return: The corresponding Python type string.
    :rtype: ```str```
    """
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return type_map.get(openapi_type, "str")


def emit_cli_sdk(spec: OpenAPI) -> str:
    """Generate the Python source code string for a CLI application."""
    body = ["import argparse", "import sys", "from client import Client", ""]

    operations = []

    if spec.paths:
        for path, path_item in spec.paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
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
                                "typ": map_openapi_type_to_python(p_type),
                                "doc": p_desc,
                                "default": None
                                if req
                                else "None",  # Hack to make optional
                            }

                    # Call python-cdd to emit argument_parser function
                    arg_ast = argparse_function(ir, "set_cli_args_" + op_id)
                    try:
                        code = ast.unparse(arg_ast)
                        body.append(code)
                        body.append("")
                        operations.append((op_id, desc))
                    except Exception as e:
                        pass

    body.append("def main():")
    body.append(
        f'    parser = argparse.ArgumentParser(description="{spec.info.title if spec.info else "API"} CLI")'
    )
    body.append('    subparsers = parser.add_subparsers(dest="command")')

    for op_id, desc in operations:
        body.append(
            f'    {op_id}_parser = subparsers.add_parser("{op_id}", help="{desc}")'
        )
        body.append(f"    set_cli_args_{op_id}({op_id}_parser)")

    body.append("")
    body.append("    args = parser.parse_args()")
    body.append("    c = Client()")
    body.append("    if not args.command:")
    body.append("        parser.print_help()")
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

    return "\\n".join(body)
