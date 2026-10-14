"""Command-line interface for the openapi-python-client."""

from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import sys
import traceback
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from io import StringIO
from pathlib import Path
from typing import Any

import libcst as cst

from openapi_client import mcp as mcp_module
from openapi_client.classes.emit import emit_models_module
from openapi_client.classes.parse import extract_classes_from_ast
from openapi_client.cli_sdk.emit import emit_cli_sdk
from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server
from openapi_client.cli_sdk.parse import extract_cli_from_ast
from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk as emit_cli_sdk_cdd
from openapi_client.dao.emit import emit_dao
from openapi_client.db.emit import emit_db
from openapi_client.fastapi.emit import emit_fastapi
from openapi_client.fastapi.emit_readme import emit_readme
from openapi_client.functions.parse import extract_functions_from_ast
from openapi_client.functions.utils import sanitize_name
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import Components, Info, OpenAPI
from openapi_client.openapi.emit import emit_openapi_json
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.seeder.emit import emit_seeder
from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.emit_server_tests import emit_server_tests
from openapi_client.tests.parse import extract_tests_from_ast


def get_version() -> str:
    """Get the installed package version of the CLI.

    Returns:
        The package version string.
    """
    try:
        return version("openapi-python-client")
    except PackageNotFoundError:  # pragma: no cover
        return "0.0.3"


def apply_env_vars_to_parser(
    parser: argparse.ArgumentParser, prefix: str = "CDD_"
) -> None:
    """Recursively set argparse default values from environment variables.

    Args:
        parser: The ArgumentParser instance to configure.
        prefix: Environment variable prefix (defaults to `'CDD_'`).
    """
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
    input_path: str,
    no_imports: bool,
    no_wrapping: bool,
    output_file: str | None,
) -> None:
    """Parse an OpenAPI spec and output JSON documentation with code snippets.

    Args:
        input_path: File path or HTTP(S) URL to the OpenAPI specification.
        no_imports: If True, omit import statements from generated snippets.
        no_wrapping: If True, omit `main()` wrapper from generated snippets.
        output_file: Optional file path to write JSON output; prints to stdout if None.
    """
    if input_path.startswith("http://") or input_path.startswith("https://"):
        req = urllib.request.Request(input_path)
        with urllib.request.urlopen(req) as response:
            content = response.read().decode("utf-8")
    else:
        spec_path = Path(input_path)
        content = spec_path.read_text(encoding="utf-8")

    spec = parse_openapi_json(content)

    endpoints: dict[str, dict[str, str]] = {}

    if spec.paths:
        for path, path_item in spec.paths.items():
            path_map: dict[str, str] = {}
            for method in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "options",
                "head",
                "trace",
            ]:
                operation = getattr(path_item, method, None)
                if operation:
                    raw_op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    op_id = sanitize_name(raw_op_id)

                    lines: list[str] = []

                    if not no_imports:
                        lines.append("import json")
                        lines.append("from generated_client import Client")
                        lines.append("")

                    if not no_wrapping:
                        lines.append("def main():")
                        lines.append(
                            '    client = Client(base_url="https://api.example.com")'
                        )

                    indent = "    " if not no_wrapping else ""

                    args: list[str] = []
                    if operation.parameters:
                        for param in operation.parameters:
                            if hasattr(param, "name"):
                                p_name = param.name.replace("-", "_")
                                lines.append(f"{indent}{p_name} = 'example'")
                                args.append(f"{p_name}={p_name}")

                    if getattr(operation, "requestBody", None):
                        lines.append(f"{indent}body = {{}}")
                        args.append("body=body")

                    args_str = ", ".join(args)
                    lines.append(f"{indent}response = client.{op_id}({args_str})")
                    lines.append(f"{indent}print(response)")

                    if not no_wrapping:
                        lines.append("")
                        lines.append('if __name__ == "__main__":')
                        lines.append("    main()")

                    path_map[method.lower()] = "\n".join(lines)

            if path_map:
                endpoints[path] = path_map

    result = {"endpoints": endpoints}

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))


def scaffold_package(out_dir: Path, is_server: bool = False) -> None:
    """Generate `pyproject.toml` scaffolding in the output directory.

    Args:
        out_dir: Target directory for the generated package.
        is_server: If True, include FastAPI, SQLAlchemy, and server dependencies.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    deps = [
        '    "pydantic==2.12.5",',
        '    "pydantic-core==2.41.5",',
        '    "urllib3",',
        '    "eval_type_backport",',
    ]

    if is_server:
        deps.extend(
            [
                '    "fastapi",',
                '    "uvicorn",',
                '    "sqlalchemy",',
                '    "faker",',
                '    "pytest",',
                '    "httpx",',
            ]
        )

    deps_str = "\n".join(deps)

    pyproject_toml = out_dir / "pyproject.toml"
    if not pyproject_toml.exists():
        pyproject_toml.write_text(
            f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "generated-project"
version = "0.0.3"
dependencies = [
{deps_str}
]

[project.optional-dependencies]
dev = [
    "pytest",
]

[tool.hatch.build.targets.wheel]
packages = ["src"]
""",
            encoding="utf-8",
        )


def scaffold_github_actions(out_dir: Path, tests: bool = False) -> None:
    """Scaffold a GitHub Actions CI workflow file.

    Args:
        out_dir: Target directory for the generated repository.
        tests: If True, include a pytest execution step in the workflow.
    """
    workflows_dir = out_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    ci_yml = workflows_dir / "ci.yml"
    if not ci_yml.exists():
        test_step = ""
        if tests:
            test_step = """
      - name: Run tests
        run: pytest test/"""

        ci_yml.write_text(
            f"""name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[dev]{test_step}
""",
            encoding="utf-8",
        )


def generate_from_openapi(
    subcommand: str,
    input_path: str | None,
    input_dir: str | None,
    output_dir: str,
    no_github_actions: bool = False,
    no_installable_package: bool = False,
    tests: bool = False,
    mcp: bool = False,
) -> None:
    """Process `from_openapi` subcommands (`to_sdk`, `to_sdk_cli`, `to_server`).

    Args:
        subcommand: The generation target (`'to_sdk'`, `'to_sdk_cli'`, or `'to_server'`).
        input_path: Path to a single OpenAPI JSON file, if provided.
        input_dir: Path to a directory of OpenAPI JSON files, if provided.
        output_dir: Destination directory or file path.
        no_github_actions: If True, skip `.github/workflows/ci.yml` generation.
        no_installable_package: If True, skip `pyproject.toml` generation.
        tests: If True, generate unit tests and mock servers.
        mcp: If True, generate MCP server, SSE server, and adapter modules.
    """
    if not output_dir:
        output_dir = "."
    out_path = Path(output_dir)
    if out_path.suffix:
        out_dir = out_path.parent
    else:
        out_dir = out_path

    out_dir.mkdir(parents=True, exist_ok=True)

    def write_generated(
        code_obj: dict[str, str] | str,
        default_filename: str,
        base_dir: Path = out_dir,
    ) -> None:
        """Write generated code mapping or string to files.

        Args:
            code_obj: Either a mapping of relative filenames to code or a single code string.
            default_filename: Filename to use when `code_obj` is a single string.
            base_dir: Base output directory.
        """
        if isinstance(code_obj, dict):
            for filename, file_content in code_obj.items():
                if file_content:
                    filepath = base_dir / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(file_content, encoding="utf-8")
        elif code_obj:
            (base_dir / default_filename).write_text(code_obj, encoding="utf-8")

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

            src_dir = out_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "__init__.py").touch(exist_ok=True)

            (src_dir / "client.py").write_text(
                generator.generate_code(), encoding="utf-8"
            )

            if spec.components and getattr(spec.components, "schemas", None):
                (src_dir / "models.py").write_text(
                    emit_models_module(spec.components.schemas), encoding="utf-8"
                )

            (src_dir / "openapi.snapshot.json").write_text(
                emit_openapi_json(spec, indent=2), encoding="utf-8"
            )

            if tests:
                test_dir = out_dir / "test"
                test_dir.mkdir(parents=True, exist_ok=True)
                (test_dir / "__init__.py").touch()
                (test_dir / "test_client.py").write_text(
                    emit_tests(spec, composable=True).code, encoding="utf-8"
                )
                (test_dir / "mock_server.py").write_text(
                    emit_mock_server(spec).code, encoding="utf-8"
                )
                write_generated(emit_dao(spec), "dao.py", base_dir=test_dir)
        elif subcommand == "to_sdk_cli":
            generator = ClientGenerator(spec)

            src_dir = out_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "__init__.py").touch(exist_ok=True)

            (src_dir / "client.py").write_text(
                generator.generate_code(), encoding="utf-8"
            )

            if spec.components and getattr(spec.components, "schemas", None):
                (src_dir / "models.py").write_text(
                    emit_models_module(spec.components.schemas), encoding="utf-8"
                )

            (src_dir / "cli_main.py").write_text(
                emit_cli_sdk_cdd(spec), encoding="utf-8"
            )
            if mcp:
                (src_dir / "mcp_server.py").write_text(
                    emit_mcp_server(spec), encoding="utf-8"
                )
                (src_dir / "mcp_sse_server.py").write_text(
                    emit_mcp_sse_server(spec), encoding="utf-8"
                )
                (src_dir / "mcp_adapter.py").write_text(
                    emit_mcp_adapter(spec), encoding="utf-8"
                )

            if tests:
                test_dir = out_dir / "test"
                test_dir.mkdir(parents=True, exist_ok=True)
                (test_dir / "__init__.py").touch()
                (test_dir / "test_client.py").write_text(
                    emit_tests(spec, composable=True).code, encoding="utf-8"
                )
                (test_dir / "mock_server.py").write_text(
                    emit_mock_server(spec).code, encoding="utf-8"
                )
                write_generated(emit_dao(spec), "dao.py", base_dir=test_dir)
        elif subcommand == "to_server":
            (out_dir / "__init__.py").touch(exist_ok=True)

            fastapi_code = emit_fastapi(spec)
            write_generated(fastapi_code, "main.py")

            sa_code = emit_sqlalchemy(spec)
            write_generated(sa_code, "models.py")

            dao_code = emit_dao(spec)
            write_generated(dao_code, "dao.py")

            db_code = emit_db(spec)
            write_generated(db_code, "db.py")

            seeder_code = emit_seeder(spec)
            write_generated(seeder_code, "seeder.py")

            test_dir = out_dir / "tests"
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "__init__.py").touch(exist_ok=True)
            test_code = emit_server_tests(spec)
            write_generated(test_code, "test_server.py", base_dir=test_dir)

            readme_code = emit_readme(spec)
            (out_dir / "README.md").write_text(readme_code, encoding="utf-8")

    if not no_installable_package:
        scaffold_package(out_dir, is_server=(subcommand == "to_server"))

    if not no_github_actions:
        scaffold_github_actions(out_dir, tests=tests)

    print(f"Successfully generated {subcommand} in {out_dir}")


def generate_to_openapi(input_path: str, output_path: str) -> None:
    """Extract an OpenAPI spec from a Python module or directory.

    Args:
        input_path: Path to a Python file or project directory.
        output_path: Output file path for the generated `openapi.json`.
    """
    if not output_path:
        output_path = "openapi.json"
    in_path = Path(input_path)
    out_path = Path(output_path)

    if in_path.is_dir():
        snapshot_json = in_path / "openapi.snapshot.json"
        if not snapshot_json.exists():
            snapshot_json = in_path / "src" / "openapi.snapshot.json"

        if snapshot_json.exists():
            spec = parse_openapi_json(snapshot_json.read_text(encoding="utf-8"))
        else:
            spec = OpenAPI(
                openapi="3.2.0",
                info=Info(title="Extracted API", version="0.0.3"),
                paths={},
                components=Components(schemas={}),
            )

        client_py = in_path / "src" / "client.py"
        if not client_py.exists():
            client_py = in_path / "client.py"

        models_py = in_path / "src" / "models.py"
        if not models_py.exists():
            models_py = in_path / "models.py"

        mock_py = in_path / "test" / "mock_server.py"
        if not mock_py.exists():
            mock_py = in_path / "mock_server.py"

        test_py = in_path / "test" / "test_client.py"
        if not test_py.exists():
            test_py = in_path / "test_client.py"

        cli_py = in_path / "src" / "cli_main.py"
        if not cli_py.exists():
            cli_py = in_path / "cli_main.py"

        if client_py.exists():
            mod = cst.parse_module(client_py.read_text(encoding="utf-8"))
            extract_classes_from_ast(mod, spec)
            extract_functions_from_ast(mod, spec)

        if models_py.exists():
            mod = cst.parse_module(models_py.read_text(encoding="utf-8"))
            extract_classes_from_ast(mod, spec)

        if mock_py.exists():
            mod = cst.parse_module(mock_py.read_text(encoding="utf-8"))
            extract_mocks_from_ast(mod, spec)

        if test_py.exists():
            mod = cst.parse_module(test_py.read_text(encoding="utf-8"))
            extract_tests_from_ast(mod, spec)

        if cli_py.exists():
            mod = cst.parse_module(cli_py.read_text(encoding="utf-8"))
            extract_cli_from_ast(mod, spec)

        out_path.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")
        print(f"Successfully extracted OpenAPI spec to {out_path}")
        return

    code = in_path.read_text(encoding="utf-8")

    if "argparse" in code and "add_parser" in code:
        spec = OpenAPI(
            openapi="3.2.0",
            info=Info(title="Extracted API", version="0.0.3"),
            paths={},
            components=Components(schemas={}),
        )
        mod = cst.parse_module(code)
        extract_cli_from_ast(mod, spec)
        out_path.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")
        print(f"Successfully extracted OpenAPI spec to {out_path}")
    else:
        spec = extract_from_code(code)
        out_path.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")
        print(f"Successfully extracted OpenAPI spec to {out_path}")


def sync_dir(
    project_dir: str,
    truth: str | None = None,
    output_dir: str | None = None,
) -> None:
    """Synchronize an OpenAPI specification with source code in a directory.

    Args:
        project_dir: Path to the directory containing source files and/or `openapi.json`.
        truth: Optional single source of truth (`'openapi'`, `'class'`, `'function'`, `'sqlalchemy'`).
        output_dir: Optional output directory; defaults to `project_dir`.
    """
    d = Path(project_dir)
    out_d = Path(output_dir) if output_dir else d

    client_py = d / "src" / "client.py"
    if not client_py.exists():
        client_py = d / "client.py"

    models_py = d / "src" / "models.py"
    if not models_py.exists():
        models_py = d / "models.py"

    mock_py = d / "test" / "mock_server.py"
    if not mock_py.exists():
        mock_py = d / "mock_server.py"

    test_py = d / "test" / "test_client.py"
    if not test_py.exists():
        test_py = d / "test_client.py"

    cli_py = d / "src" / "cli_main.py"
    if not cli_py.exists():
        cli_py = d / "cli_main.py"
    openapi_json = d / "openapi.json"

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Extracted API", version="0.0.3"),
        paths={},
        components=Components(schemas={}),
    )

    if truth == "openapi" and openapi_json.exists():
        spec = parse_openapi_json(openapi_json.read_text(encoding="utf-8"))
    else:
        if client_py.exists() and truth in (None, "class", "function"):
            mod = cst.parse_module(client_py.read_text(encoding="utf-8"))
            if truth in (None, "class"):
                extract_classes_from_ast(mod, spec)
            if truth in (None, "function"):
                extract_functions_from_ast(mod, spec)

        if models_py.exists() and truth in (None, "class"):
            mod = cst.parse_module(models_py.read_text(encoding="utf-8"))
            extract_classes_from_ast(mod, spec)

        if mock_py.exists() and truth in (None, "function"):
            mod = cst.parse_module(mock_py.read_text(encoding="utf-8"))
            extract_mocks_from_ast(mod, spec)

        if test_py.exists() and truth is None:
            mod = cst.parse_module(test_py.read_text(encoding="utf-8"))
            extract_tests_from_ast(mod, spec)

        if cli_py.exists() and truth is None:
            mod = cst.parse_module(cli_py.read_text(encoding="utf-8"))
            extract_cli_from_ast(mod, spec)

        if (
            openapi_json.exists()
            and not spec.paths
            and (
                spec.components is None or not getattr(spec.components, "schemas", None)
            )
        ):
            spec = parse_openapi_json(openapi_json.read_text(encoding="utf-8"))

    out_openapi_json = out_d / openapi_json.relative_to(d)
    out_openapi_json.parent.mkdir(parents=True, exist_ok=True)
    out_openapi_json.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")

    generator = ClientGenerator(spec)
    out_client_py = out_d / client_py.relative_to(d)
    out_client_py.parent.mkdir(parents=True, exist_ok=True)
    (out_client_py.parent / "__init__.py").touch(exist_ok=True)
    out_client_py.write_text(generator.generate_code(), encoding="utf-8")

    if spec.components and getattr(spec.components, "schemas", None):
        out_models_py = out_d / models_py.relative_to(d)
        out_models_py.parent.mkdir(parents=True, exist_ok=True)
        (out_models_py.parent / "__init__.py").touch(exist_ok=True)
        out_models_py.write_text(
            emit_models_module(spec.components.schemas), encoding="utf-8"
        )

    out_test_py = out_d / test_py.relative_to(d)
    out_test_py.parent.mkdir(parents=True, exist_ok=True)
    (out_test_py.parent / "__init__.py").touch(exist_ok=True)
    out_test_py.write_text(emit_tests(spec).code, encoding="utf-8")

    out_mock_py = out_d / mock_py.relative_to(d)
    out_mock_py.parent.mkdir(parents=True, exist_ok=True)
    (out_mock_py.parent / "__init__.py").touch(exist_ok=True)
    out_mock_py.write_text(emit_mock_server(spec).code, encoding="utf-8")

    def write_generated_local(
        code_obj: dict[str, str] | str,
        default_filename: str,
        base_dir: Path = out_d,
    ) -> None:
        """Write generated code to local files.

        Args:
            code_obj: Mapping of relative file paths to code, or a single code string.
            default_filename: Default filename when `code_obj` is a string.
            base_dir: Destination base directory.
        """
        if isinstance(code_obj, dict):
            for filename, file_content in code_obj.items():
                if file_content:
                    filepath = base_dir / filename
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(file_content, encoding="utf-8")
        elif code_obj:
            (base_dir / default_filename).write_text(code_obj, encoding="utf-8")

    write_generated_local(emit_dao(spec), "dao.py")

    db_py = d / "src" / "db.py"
    if not db_py.exists():
        db_py = d / "db.py"

    out_db_py = out_d / db_py.relative_to(d)
    out_db_py.parent.mkdir(parents=True, exist_ok=True)
    out_db_py.write_text(emit_db(spec), encoding="utf-8")

    write_generated_local(emit_seeder(spec), "seeder.py")

    if cli_py.exists():
        out_cli_py = out_d / cli_py.relative_to(d)
        out_cli_py.parent.mkdir(parents=True, exist_ok=True)
        (out_cli_py.parent / "__init__.py").touch(exist_ok=True)
        out_cli_py.write_text(emit_cli_sdk(spec), encoding="utf-8")

    if out_d != d:
        print(f"Successfully synced {project_dir} to {output_dir}")
    else:
        print(f"Successfully synced {project_dir}")


def run_mcp_server() -> None:
    """Run the generator as an MCP server over stdio."""

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
        sys.stdout.write(json.dumps(resp) + "\n")
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
                        "capabilities": {"tools": {}, "resources": {}},
                        "serverInfo": {
                            "name": "cdd-generator",
                            "version": get_version(),
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
                            generate_to_openapi(
                                args.get("input_path"), args.get("output_path")
                            )
                        elif tool_name == "from_openapi":
                            generate_from_openapi(
                                args.get("subcommand", "to_sdk"),
                                args.get("input_path"),
                                None,
                                args.get("output_dir", "."),
                            )
                        elif tool_name == "sync_dir":
                            sync_dir(args.get("project_dir"))
                        elif tool_name == "to_docs_json":
                            generate_docs_json(
                                args.get("input_path"),
                                False,
                                False,
                                args.get("output_file"),
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
                except Exception as e:
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
        except Exception as e:
            if "req_id" in locals() and req_id is not None:
                send_response(req_id, error={"code": -32603, "message": str(e)})


def serve_json_rpc(port: int, listen: str) -> None:
    """Run a JSON-RPC 2.0 HTTP server exposing the CLI subcommands.

    Args:
        port: TCP port to listen on.
        listen: Host address to bind to.
    """

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
                    generate_to_openapi(params.get("input"), params.get("output"))
                    result = "Success"
                elif method in (
                    "from_openapi_to_sdk",
                    "from_openapi_to_sdk_cli",
                    "from_openapi_to_server",
                ):
                    subcommand = method.replace("from_openapi_", "")
                    generate_from_openapi(
                        subcommand,
                        params.get("input"),
                        params.get("input_dir"),
                        params.get("output"),
                        params.get("no_github_actions", False),
                        params.get("no_installable_package", False),
                        params.get("tests", False),
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

            response: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id}
            if error:
                response["error"] = error
            else:
                response["result"] = result

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

    server_address = (listen, port)
    httpd = http.server.HTTPServer(server_address, JSONRPCRequestHandler)
    print(f"Starting JSON-RPC server on {listen}:{port}")
    httpd.serve_forever()


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Compiler Driven Development (CDD) compiler and transpiler."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=get_version(),
    )
    subparsers = parser.add_subparsers(dest="command")

    from_openapi_parser = subparsers.add_parser(
        "from_openapi", help="Generate code from an OpenAPI specification."
    )

    from_openapi_subparsers = from_openapi_parser.add_subparsers(
        dest="from_openapi_command", required=True
    )

    for subcmd in ["to_sdk", "to_sdk_cli", "to_server"]:
        if subcmd == "to_sdk_cli":
            help_text = (
                "Generate a client SDK with a CLI from an OpenAPI specification."
            )
        elif subcmd == "to_sdk":
            help_text = "Generate a client SDK from an OpenAPI specification."
        else:
            help_text = "Generate server boilerplate, models, and routing logic from an OpenAPI specification."

        p = from_openapi_subparsers.add_parser(subcmd, help=help_text)
        group = p.add_mutually_exclusive_group(required=False)
        group.add_argument(
            "-i",
            "-f",
            "--input",
            type=str,
            help="Path or URL to the OpenAPI specification.",
        )
        group.add_argument(
            "-d",
            "--input-dir",
            type=str,
            help="Directory containing OpenAPI specifications.",
        )
        p.add_argument(
            "-o",
            "--output",
            type=str,
            default=".",
            help="Output file or directory path.",
        )
        p.add_argument(
            "--no-github-actions",
            action="store_true",
            help="Do not generate GitHub Actions scaffolding.",
        )
        p.add_argument(
            "--no-installable-package",
            action="store_true",
            help="Do not generate installable package scaffolding.",
        )
        p.add_argument(
            "--tests",
            action="store_true",
            help="Generate integration tests and mocks.",
        )
        p.add_argument(
            "--mcp",
            action="store_true",
            help="Generate Model Context Protocol (MCP) server and adapter.",
        )

    to_openapi_parser = subparsers.add_parser(
        "to_openapi",
        help="Parse the existing codebase and extract an authoritative OpenAPI specification.",
    )
    to_openapi_parser.add_argument(
        "-i",
        "-f",
        "--input",
        type=str,
        help="Path to source code directory or file",
        required=True,
    )
    to_openapi_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="openapi.json",
        help="Output file or directory path",
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync a directory containing client.py, mock_server.py, test_client.py, cli_main.py",
    )
    sync_parser.add_argument(
        "-i",
        "-d",
        "--input",
        type=str,
        required=True,
        help="Path to directory containing Python files to sync",
    )
    sync_parser.add_argument(
        "-t",
        "--truth",
        type=str,
        choices=["class", "sqlalchemy", "function", "openapi"],
        help="Designate a single source of truth for synchronization.",
    )
    sync_parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output directory path",
    )

    docs_parser = subparsers.add_parser(
        "to_docs_json",
        help="Generate JSON documentation with code snippets for an OpenAPI specification.",
    )
    docs_parser.add_argument(
        "-i",
        "-f",
        "--input",
        type=str,
        required=True,
        help="Path or URL to the OpenAPI specification.",
    )
    docs_parser.add_argument(
        "--no-imports", action="store_true", help="Omit the imports field."
    )
    docs_parser.add_argument(
        "--no-wrapping", action="store_true", help="Omit the wrapper fields."
    )
    docs_parser.add_argument(
        "-o", "--output", type=str, help="Output file or directory path."
    )

    server_parser = subparsers.add_parser(
        "serve_json_rpc",
        help="Expose CLI interface as a JSON-RPC server.",
    )
    server_parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Port to listen on"
    )
    server_parser.add_argument(
        "-l", "--listen", type=str, default="0.0.0.0", help="Address to listen on"
    )

    subparsers.add_parser(
        "mcp", help="Run the Model Context Protocol server via stdio."
    )

    apply_env_vars_to_parser(parser)
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "sync":
        sync_dir(
            args.input, getattr(args, "truth", None), getattr(args, "output", None)
        )
    elif args.command == "from_openapi":
        subcmd = args.from_openapi_command
        if not args.input and not getattr(args, "input_dir", None):
            from_openapi_parser.print_help()
            sys.exit(1)
        generate_from_openapi(
            subcmd,
            args.input,
            getattr(args, "input_dir", None),
            args.output,
            args.no_github_actions,
            args.no_installable_package,
            getattr(args, "tests", False),
            getattr(args, "mcp", False),
        )
    elif args.command == "to_openapi":
        in_path = args.input
        generate_to_openapi(in_path, args.output)
    elif args.command == "to_docs_json":
        generate_docs_json(args.input, args.no_imports, args.no_wrapping, args.output)
    elif args.command == "serve_json_rpc":
        serve_json_rpc(args.port, args.listen)
    elif args.command == "mcp":
        run_mcp_server()


if __name__ == "__main__":  # pragma: no cover
    main()
