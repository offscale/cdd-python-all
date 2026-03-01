"""Command-line interface for the openapi-python-client."""

import argparse
import sys
import os
import json
from pathlib import Path
import libcst as cst
from importlib.metadata import version, PackageNotFoundError

from openapi_client.models import OpenAPI, Info, Components
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.parse import extract_tests_from_ast
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.cli_sdk.emit import emit_cli_sdk
from openapi_client.cli_sdk.parse import extract_cli_from_ast

from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.openapi.emit import emit_openapi_json


def get_version() -> str:
    """Get the version of the CLI."""
    try:
        return version("openapi-python-client")
    except PackageNotFoundError:  # pragma: no cover
        return "0.0.1"


def apply_env_vars_to_parser(
    parser: argparse.ArgumentParser, prefix: str = "CDD_PYTHON_"
):
    """Recursively set argparse default values from environment variables."""
    for action in parser._actions:
        if action.dest and action.dest != "help" and action.dest != "==SUPPRESS==":
            env_var = prefix + action.dest.upper()
            val = os.environ.get(env_var)
            if val is not None:
                if isinstance(action, argparse._StoreTrueAction):
                    action.default = val.lower() in ("true", "1", "yes")
                elif isinstance(action, argparse._StoreFalseAction):
                    action.default = val.lower() not in ("true", "1", "yes")
                else:
                    action.default = val
        if isinstance(action, argparse._SubParsersAction):
            for subparser in action.choices.values():
                apply_env_vars_to_parser(subparser, prefix)


def generate_docs_json(
    input_path: str, no_imports: bool, no_wrapping: bool, output_file: str
) -> None:
    """Parse OpenAPI spec and output JSON documentation."""
    spec_path = Path(input_path)
    spec = parse_openapi_json(spec_path.read_text(encoding="utf-8"))

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

                    code = {}
                    if not no_imports:
                        code["imports"] = "from client import Client"
                    if not no_wrapping:
                        code["wrapper_start"] = (
                            'def main():\n    client = Client(base_url="https://api.example.com")'
                        )
                        code["wrapper_end"] = 'if __name__ == "__main__":\n    main()'

                    args = []
                    if operation.parameters:
                        for param in operation.parameters:
                            if hasattr(param, "name"):
                                p_name = param.name.replace("-", "_")
                                args.append(f"{p_name}={p_name}")

                    args_str = ", ".join(args)
                    indent = "    " if not no_wrapping else ""
                    code["snippet"] = f"{indent}response = client.{op_id}({args_str})"

                    op_data = {"method": method.upper(), "path": path, "code": code}
                    if operation.operationId:
                        op_data["operationId"] = operation.operationId

                    operations.append(op_data)

    output = [{"language": "python", "operations": operations}]

    out_json = json.dumps(output, indent=2)
    if output_file:
        Path(output_file).write_text(out_json, encoding="utf-8")
    else:
        print(out_json)


def scaffold_package(out_dir: Path):
    """Generate pyproject.toml and github actions."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate pyproject.toml
    pyproject_toml = out_dir / "pyproject.toml"
    if not pyproject_toml.exists():
        pyproject_toml.write_text(
            """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "generated-client"
version = "0.0.1"
dependencies = [
    "pydantic>=2.0",
    "urllib3",
]
""",
            encoding="utf-8",
        )


def scaffold_github_actions(out_dir: Path):
    """Scaffold GitHub actions CI file."""
    workflows_dir = out_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    ci_yml = workflows_dir / "ci.yml"
    if not ci_yml.exists():
        ci_yml.write_text(
            """name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[dev]
      - name: Run tests
        run: pytest
""",
            encoding="utf-8",
        )


def process_from_openapi(
    subcommand: str,
    input_path: str,
    input_dir: str,
    output_dir: str,
    no_github_actions: bool = False,
    no_installable_package: bool = False,
) -> None:
    """Process from_openapi subcommands."""
    if not output_dir:
        output_dir = "."
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if input_path:
        spec_path = Path(input_path)
        specs = [parse_openapi_json(spec_path.read_text(encoding="utf-8"))]
    elif input_dir:
        specs = []
        for p in Path(input_dir).glob("*.json"):
            specs.append(parse_openapi_json(p.read_text(encoding="utf-8")))
    else:
        print("Either --input or --input-dir is required.")
        sys.exit(1)

    for spec in specs:
        if subcommand == "to_sdk":
            generator = ClientGenerator(spec)
            (out_dir / "client.py").write_text(
                generator.generate_code(), encoding="utf-8"
            )
            (out_dir / "test_client.py").write_text(
                emit_tests(spec).code, encoding="utf-8"
            )
        elif subcommand == "to_sdk_cli":
            generator = ClientGenerator(spec)
            (out_dir / "client.py").write_text(
                generator.generate_code(), encoding="utf-8"
            )
            (out_dir / "cli_main.py").write_text(emit_cli_sdk(spec), encoding="utf-8")
        elif subcommand == "to_server":
            mock_module = emit_mock_server(spec)
            (out_dir / "mock_server.py").write_text(mock_module.code, encoding="utf-8")

    if not no_installable_package:
        scaffold_package(out_dir)

    if not no_github_actions:
        scaffold_github_actions(out_dir)

    print(f"Successfully generated {subcommand} in {out_dir}")


def sync_to_openapi(python_path: str, output_path: str) -> None:
    """Extract an OpenAPI spec from a Python module."""
    if not output_path:
        output_path = "openapi.json"
    py_path = Path(python_path)
    out_path = Path(output_path)

    code = py_path.read_text(encoding="utf-8")

    if "argparse" in code and "add_parser" in code:
        spec = OpenAPI(
            **{
                "openapi": "3.2.0",
                "info": Info(title="Extracted API", version="0.0.1"),
                "paths": {},
                "components": Components(schemas={}),
            }
        )  # type: ignore
        mod = cst.parse_module(code)
        extract_cli_from_ast(mod, spec)
        out_path.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")
        print(f"Successfully extracted OpenAPI spec to {out_path}")
    else:
        spec = extract_from_code(code)
        out_path.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")
        print(f"Successfully extracted OpenAPI spec to {out_path}")


def sync_dir(project_dir: str) -> None:
    """Sync client, mock, test, cli files in a directory to a unified OpenAPI spec, and regenerate all."""
    d = Path(project_dir)

    client_py = d / "client.py"
    mock_py = d / "mock_server.py"
    test_py = d / "test_client.py"
    cli_py = d / "cli_main.py"
    openapi_json = d / "openapi.json"

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Extracted API", version="0.0.1"),
            "paths": {},
            "components": Components(schemas={}),
        }
    )  # type: ignore

    if client_py.exists():
        from openapi_client.classes.parse import extract_classes_from_ast
        from openapi_client.functions.parse import extract_functions_from_ast

        mod = cst.parse_module(client_py.read_text(encoding="utf-8"))
        extract_classes_from_ast(mod, spec)
        extract_functions_from_ast(mod, spec)

    if mock_py.exists():
        mod = cst.parse_module(mock_py.read_text(encoding="utf-8"))
        extract_mocks_from_ast(mod, spec)

    if test_py.exists():
        mod = cst.parse_module(test_py.read_text(encoding="utf-8"))
        extract_tests_from_ast(mod, spec)

    if cli_py.exists():
        mod = cst.parse_module(cli_py.read_text(encoding="utf-8"))
        extract_cli_from_ast(mod, spec)

    if (
        openapi_json.exists()
        and not spec.paths
        and (spec.components is None or not getattr(spec.components, "schemas", None))
    ):
        spec = parse_openapi_json(openapi_json.read_text(encoding="utf-8"))

    openapi_json.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")

    generator = ClientGenerator(spec)
    client_py.write_text(generator.generate_code(), encoding="utf-8")
    test_py.write_text(emit_tests(spec).code, encoding="utf-8")
    mock_py.write_text(emit_mock_server(spec).code, encoding="utf-8")
    if cli_py.exists():
        cli_py.write_text(emit_cli_sdk(spec), encoding="utf-8")

    print(f"Successfully synced {project_dir}")


def run_json_rpc_server(port: int, listen: str):
    """Run a JSON-RPC 2.0 server exposing the CLI subcommands."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import traceback

    class JSONRPCRequestHandler(BaseHTTPRequestHandler):
        """Handler for JSON-RPC requests."""

        def do_POST(self):
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

            result = None
            error = None

            try:
                if method == "to_openapi":
                    sync_to_openapi(params.get("file"), params.get("output"))
                    result = "Success"
                elif method == "from_openapi":
                    process_from_openapi(
                        params.get("subcommand"),
                        params.get("input"),
                        params.get("input_dir"),
                        params.get("output"),
                        params.get("no_github_actions", False),
                        params.get("no_installable_package", False),
                    )
                    result = "Success"
                elif method == "to_docs_json":
                    generate_docs_json(
                        params.get("input"),
                        params.get("no_imports", False),
                        params.get("no_wrapping", False),
                        params.get("output"),
                    )
                    result = "Success"
                elif method == "sync":
                    sync_dir(params.get("dir"))
                    result = "Success"
                else:
                    error = {"code": -32601, "message": "Method not found"}
            except Exception as e:
                error = {
                    "code": -32000,
                    "message": str(e),
                    "data": traceback.format_exc(),
                }

            response = {"jsonrpc": "2.0", "id": req_id}
            if error:
                response["error"] = error
            else:
                response["result"] = result

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

    server_address = (listen, port)
    httpd = HTTPServer(server_address, JSONRPCRequestHandler)
    print(f"Starting JSON-RPC server on {listen}:{port}")
    httpd.serve_forever()


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="CDD Python Client generator and extractor."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"cdd-python {get_version()}",
    )
    subparsers = parser.add_subparsers(dest="command")

    from_openapi_parser = subparsers.add_parser(
        "from_openapi", help="Generate code from OpenAPI"
    )
    from_openapi_subparsers = from_openapi_parser.add_subparsers(
        dest="from_openapi_command"
    )

    for subcmd in ["to_sdk", "to_sdk_cli", "to_server"]:
        p = from_openapi_subparsers.add_parser(subcmd)
        group = p.add_mutually_exclusive_group(required=False)
        group.add_argument("-i", "--input", type=str, help="Path to OpenAPI JSON file")
        group.add_argument(
            "--input-dir", type=str, help="Directory containing OpenAPI specs"
        )
        p.add_argument("-o", "--output", type=str, default=".", help="Output directory")
        p.add_argument(
            "--no-github-actions",
            action="store_true",
            help="Do not generate GitHub Actions",
        )
        p.add_argument(
            "--no-installable-package",
            action="store_true",
            help="Do not generate installable package scaffolding",
        )

    to_openapi_parser = subparsers.add_parser(
        "to_openapi", help="Extract OpenAPI from code"
    )
    to_openapi_parser.add_argument(
        "-f", "--file", type=str, required=True, help="Path to Python source file"
    )
    to_openapi_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="openapi.json",
        help="Output OpenAPI JSON file",
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync a directory containing client.py, mock_server.py, test_client.py, cli_main.py",
    )
    sync_parser.add_argument(
        "--dir",
        type=str,
        required=True,
        help="Path to directory containing Python files to sync",
    )

    docs_parser = subparsers.add_parser(
        "to_docs_json", help="Generate JSON documentation"
    )
    docs_parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Path or URL to the OpenAPI specification",
    )
    docs_parser.add_argument(
        "--no-imports", action="store_true", help="Omit the imports field"
    )
    docs_parser.add_argument(
        "--no-wrapping", action="store_true", help="Omit the wrapper fields"
    )
    docs_parser.add_argument(
        "-o", "--output", type=str, help="Output JSON file (defaults to stdout)"
    )

    server_parser = subparsers.add_parser("server_json_rpc", help="Run JSON-RPC server")
    server_parser.add_argument(
        "--port", type=int, default=8080, help="Port to listen on"
    )
    server_parser.add_argument(
        "--listen", type=str, default="0.0.0.0", help="Address to listen on"
    )

    apply_env_vars_to_parser(parser)
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "sync":
        sync_dir(args.dir)
    elif args.command == "from_openapi":
        if not args.from_openapi_command:
            from_openapi_parser.print_help()
            sys.exit(0)
        process_from_openapi(
            args.from_openapi_command,
            args.input,
            args.input_dir,
            args.output,
            args.no_github_actions,
            args.no_installable_package,
        )
    elif args.command == "to_openapi":
        sync_to_openapi(args.file, args.output)
    elif args.command == "to_docs_json":
        generate_docs_json(args.input, args.no_imports, args.no_wrapping, args.output)
    elif args.command == "server_json_rpc":
        run_json_rpc_server(args.port, args.listen)


if __name__ == "__main__":  # pragma: no cover
    main()
