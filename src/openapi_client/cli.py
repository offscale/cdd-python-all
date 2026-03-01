"""Command-line interface for the openapi-python-client."""

import argparse
import sys
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

from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.openapi.emit import emit_openapi_json


def get_version() -> str:
    """Get the version of the CLI."""
    try:
        return version("openapi-python-client")
    except PackageNotFoundError:  # pragma: no cover
        return "0.1.0"


def generate_docs_json(input_path: str, no_imports: bool, no_wrapping: bool) -> None:
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

                    # Basic snippet with arguments
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

    print(json.dumps(output, indent=2))


def sync_from_openapi(openapi_path: str, output_dir: str) -> None:
    """Generate Python client, tests, and mocks from an OpenAPI spec."""
    spec_path = Path(openapi_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = parse_openapi_json(spec_path.read_text(encoding="utf-8"))

    # Generate client
    generator = ClientGenerator(spec)
    client_code = generator.generate_code()
    (out_dir / "client.py").write_text(client_code, encoding="utf-8")

    # Generate tests
    test_module = emit_tests(spec)
    (out_dir / "test_client.py").write_text(test_module.code, encoding="utf-8")

    # Generate mocks
    mock_module = emit_mock_server(spec)
    (out_dir / "mock_server.py").write_text(mock_module.code, encoding="utf-8")

    print(f"Successfully generated Python client, tests, and mocks in {out_dir}")


def sync_to_openapi(python_path: str, output_path: str) -> None:
    """Extract an OpenAPI spec from a Python client module."""
    py_path = Path(python_path)
    out_path = Path(output_path)

    code = py_path.read_text(encoding="utf-8")
    spec = extract_from_code(code)

    out_path.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")
    print(f"Successfully extracted OpenAPI spec to {out_path}")


def sync_dir(project_dir: str) -> None:
    """Sync client, mock, and test files in a directory to a unified OpenAPI spec, and regenerate all."""
    d = Path(project_dir)

    client_py = d / "client.py"
    mock_py = d / "mock_server.py"
    test_py = d / "test_client.py"
    openapi_json = d / "openapi.json"

    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Extracted API", version="1.0.0"),
            "paths": {},
            "components": Components(schemas={}),
        }
    )  # type: ignore

    # Extract from client.py
    if client_py.exists():
        from openapi_client.classes.parse import extract_classes_from_ast
        from openapi_client.functions.parse import extract_functions_from_ast

        mod = cst.parse_module(client_py.read_text(encoding="utf-8"))
        extract_classes_from_ast(mod, spec)
        extract_functions_from_ast(mod, spec)

    # Extract from mock_server.py
    if mock_py.exists():
        mod = cst.parse_module(mock_py.read_text(encoding="utf-8"))
        extract_mocks_from_ast(mod, spec)

    # Extract from test_client.py
    if test_py.exists():
        mod = cst.parse_module(test_py.read_text(encoding="utf-8"))
        extract_tests_from_ast(mod, spec)

    # If the spec is completely empty, see if we have openapi.json
    if (
        openapi_json.exists()
        and not spec.paths
        and (spec.components is None or not getattr(spec.components, "schemas", None))
    ):
        spec = parse_openapi_json(openapi_json.read_text(encoding="utf-8"))

    # Write back the merged spec
    openapi_json.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")

    # Regenerate files
    generator = ClientGenerator(spec)
    client_py.write_text(generator.generate_code(), encoding="utf-8")

    test_module = emit_tests(spec)
    test_py.write_text(test_module.code, encoding="utf-8")

    mock_module = emit_mock_server(spec)
    mock_py.write_text(mock_module.code, encoding="utf-8")

    print(f"Successfully synced {project_dir}")


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
    from_openapi_parser.add_argument(
        "-i", "--input", type=str, required=True, help="Path to OpenAPI JSON file"
    )
    from_openapi_parser.add_argument(
        "-o", "--output", type=str, default=".", help="Output directory"
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
        help="Sync a directory containing client.py, mock_server.py, test_client.py",
    )
    sync_parser.add_argument(
        "--dir",
        type=str,
        required=True,
        help="Path to directory containing client.py, mock_server.py, test_client.py",
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "sync":
        sync_dir(args.dir)
    elif args.command == "from_openapi":
        sync_from_openapi(args.input, args.output)
    elif args.command == "to_openapi":
        sync_to_openapi(args.file, args.output)
    elif args.command == "to_docs_json":
        generate_docs_json(args.input, args.no_imports, args.no_wrapping)


if __name__ == "__main__":  # pragma: no cover
    main()
