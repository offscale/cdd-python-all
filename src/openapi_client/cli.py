"""Command-line interface for the openapi-python-client."""

import argparse
import sys
from pathlib import Path
import libcst as cst

from openapi_client.models import OpenAPI, Info, Components
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.parse import extract_tests_from_ast
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast

from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.openapi.emit import emit_openapi_json


def sync_to_python(openapi_path: str, output_dir: str) -> None:
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
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Sync between OpenAPI and Python")
    sync_parser.add_argument(
        "--from-openapi", type=str, help="Path to OpenAPI JSON file"
    )
    sync_parser.add_argument(
        "--to-python", type=str, help="Path to output Python directory"
    )
    sync_parser.add_argument(
        "--from-python", type=str, help="Path to Python client file"
    )
    sync_parser.add_argument(
        "--to-openapi", type=str, help="Path to output OpenAPI JSON file"
    )
    sync_parser.add_argument(
        "--dir",
        type=str,
        help="Path to directory containing client.py, mock_server.py, test_client.py",
    )

    args = parser.parse_args()

    if args.command == "sync":
        if args.dir:
            sync_dir(args.dir)
        elif args.from_openapi and args.to_python:
            sync_to_python(args.from_openapi, args.to_python)
        elif args.from_python and args.to_openapi:
            sync_to_openapi(args.from_python, args.to_openapi)
        else:
            print(
                "Invalid sync arguments. Use either --dir, --from-openapi & --to-python OR --from-python & --to-openapi."
            )
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()

"""
Command-line interface for the openapi-python-client.
"""
