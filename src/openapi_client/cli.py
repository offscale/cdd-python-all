"""Command-line interface for the openapi-python-client."""

from __future__ import annotations

import argparse
import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import libcst as cst

from openapi_client.arazzo.emit import emit_arazzo_json
from openapi_client.arazzo.parse import parse_arazzo_json, resolve_source_descriptions
from openapi_client.arazzo_models import Arazzo
from openapi_client.classes.emit import emit_models_module
from openapi_client.classes.parse import extract_classes_from_ast
from openapi_client.cli_sdk.emit_arazzo import emit_arazzo_cli_code
from openapi_client.cli_sdk.emit_mcp import emit_mcp_server
from openapi_client.cli_sdk.emit_mcp_adapter import emit_mcp_adapter
from openapi_client.cli_sdk.emit_mcp_sse import emit_mcp_sse_server
from openapi_client.cli_sdk.parse import extract_cli_from_ast
from openapi_client.cli_sdk.parse_arazzo import extract_arazzo_from_cli_code
from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk as emit_cli_sdk_cdd
from openapi_client.dao.emit import emit_dao
from openapi_client.db.emit import emit_db
from openapi_client.docs_json import generate_docs_json
from openapi_client.fastapi.emit import emit_fastapi
from openapi_client.fastapi.emit_arazzo import emit_fastapi_arazzo_routes
from openapi_client.fastapi.emit_readme import emit_readme
from openapi_client.fastapi.parse_arazzo import extract_arazzo_from_fastapi_code
from openapi_client.functions.parse import extract_functions_from_ast
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import Components, Info, OpenAPI
from openapi_client.openapi.emit import emit_openapi_json
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.scaffolding import (
    scaffold_github_actions,
    scaffold_package,
    write_generated,
)
from openapi_client.seeder.emit import emit_seeder
from openapi_client.servers.json_rpc import JSONRPCRequestHandler, serve_json_rpc
from openapi_client.servers.mcp_stdio import run_mcp_server
from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy
from openapi_client.sqlalchemy_cdd.parse import parse_sqlalchemy_cdd
from openapi_client.sync import sync_dir
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.emit_arazzo_tests import emit_arazzo_tests_code
from openapi_client.tests.emit_server_tests import emit_server_tests
from openapi_client.tests.parse import extract_tests_from_ast
from openapi_client.tests.parse_arazzo_tests import extract_arazzo_from_test_code
from openapi_client.workflows.emit import emit_workflows_code
from openapi_client.workflows.parse import extract_arazzo_from_code

__all__ = [
    "JSONRPCRequestHandler",
    "apply_env_vars_to_parser",
    "emit_dao",
    "emit_seeder",
    "generate_docs_json",
    "generate_from_arazzo",
    "generate_from_openapi",
    "generate_to_arazzo",
    "generate_to_openapi",
    "get_version",
    "main",
    "run_mcp_server",
    "serve_json_rpc",
    "sync_dir",
]


def _resolve_output_dir(output_dir: str) -> Path:
    """Resolve an output directory or file path to its target directory.

    Args:
        output_dir: Destination directory or file path string.

    Returns:
        The resolved directory `Path`.
    """
    if not output_dir:
        output_dir = "."
    out_path = Path(output_dir)
    if out_path.suffix.lower() in (".py", ".json", ".yaml", ".yml"):
        return out_path.parent
    return out_path


def get_version() -> str:
    """Get the installed package version of the CLI.

    Returns:
        The package version string.
    """
    try:
        return version("openapi-python-client")
    except PackageNotFoundError:  # pragma: no cover
        return "0.0.4"


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
                elif action.type in (int, float) and callable(action.type):
                    action.default = action.type(val)
                else:
                    action.default = val
        if isinstance(action, argparse._SubParsersAction):
            for subparser in action.choices.values():
                apply_env_vars_to_parser(subparser, prefix)


def generate_from_openapi(
    subcommand: str,
    input_path: str | None,
    input_dir: str | None,
    output_dir: str,
    no_github_actions: bool = False,
    no_installable_package: bool = False,
    tests: bool = False,
    mcp: bool = False,
    arazzo_path: str | None = None,
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
        arazzo_path: Optional path to a companion Arazzo 1.1.0 specification to bundle.
    """
    out_dir = _resolve_output_dir(output_dir)
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

            src_dir = out_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "__init__.py").touch(exist_ok=True)

            (src_dir / "client.py").write_text(
                generator.generate_code(), encoding="utf-8"
            )
            if spec.components and spec.components.schemas:
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

            if spec.components and spec.components.schemas:
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
            write_generated(fastapi_code, "main.py", base_dir=out_dir)

            sa_code = emit_sqlalchemy(spec)
            write_generated(sa_code, "models.py", base_dir=out_dir)

            dao_code = emit_dao(spec)
            write_generated(dao_code, "dao.py", base_dir=out_dir)

            db_code = emit_db(spec)
            write_generated(db_code, "db.py", base_dir=out_dir)

            seeder_code = emit_seeder(spec)
            write_generated(seeder_code, "seeder.py", base_dir=out_dir)

            test_dir = out_dir / "tests"
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "__init__.py").touch(exist_ok=True)
            test_code = emit_server_tests(spec)
            write_generated(test_code, "test_server.py", base_dir=test_dir)

            readme_code = emit_readme(spec)
            (out_dir / "README.md").write_text(readme_code, encoding="utf-8")

    if arazzo_path:
        generate_from_arazzo(
            subcommand=subcommand,
            input_path=arazzo_path,
            input_dir=None,
            output_dir=str(out_dir),
            no_github_actions=True,
            no_installable_package=True,
            tests=tests,
        )

    if not no_installable_package:
        scaffold_package(out_dir, is_server=(subcommand == "to_server"))

    if not no_github_actions:
        scaffold_github_actions(out_dir, tests=tests)

    print(f"Successfully generated {subcommand} in {out_dir}")


def generate_from_arazzo(
    subcommand: str,
    input_path: str | None,
    input_dir: str | None,
    output_dir: str,
    no_github_actions: bool = False,
    no_installable_package: bool = False,
    tests: bool = False,
) -> None:
    """Process `from_arazzo` subcommands (`to_sdk`, `to_sdk_cli`, `to_server`, `to_tests`).

    Args:
        subcommand: The generation target (`'to_sdk'`, `'to_sdk_cli'`, `'to_server'`, or `'to_tests'`).
        input_path: Path to a single Arazzo JSON file, if provided.
        input_dir: Path to a directory of Arazzo JSON files, if provided.
        output_dir: Destination directory or file path.
        no_github_actions: If True, skip `.github/workflows/ci.yml` generation.
        no_installable_package: If True, skip `pyproject.toml` generation.
        tests: If True, generate end-to-end workflow pytest suites.
    """
    out_dir = _resolve_output_dir(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    specs: list[tuple[Path, Arazzo]] = []
    if input_path:
        spec_path = Path(input_path)
        specs.append(
            (
                spec_path.parent,
                parse_arazzo_json(
                    spec_path.read_text(encoding="utf-8"), spec_path.parent
                ),
            )
        )
    elif input_dir:
        for p in Path(input_dir).glob("*.json"):
            raw_text = p.read_text(encoding="utf-8")
            raw_obj = json.loads(raw_text)
            if isinstance(raw_obj, dict) and "arazzo" in raw_obj:
                specs.append((p.parent, parse_arazzo_json(raw_text, p.parent)))
    else:
        print("Either --input or --input-dir is required.")
        sys.exit(1)

    for base_path, spec in specs:
        sources = resolve_source_descriptions(spec, base_path)
        if subcommand == "to_sdk":
            src_dir = out_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "__init__.py").touch(exist_ok=True)
            (src_dir / "workflows.py").write_text(
                emit_workflows_code(spec, sources), encoding="utf-8"
            )
            (src_dir / "arazzo.snapshot.json").write_text(
                emit_arazzo_json(spec, indent=2), encoding="utf-8"
            )
            if tests:
                test_dir = out_dir / "test"
                test_dir.mkdir(parents=True, exist_ok=True)
                (test_dir / "__init__.py").touch(exist_ok=True)
                (test_dir / "test_workflows.py").write_text(
                    emit_arazzo_tests_code(spec), encoding="utf-8"
                )
        elif subcommand == "to_sdk_cli":
            src_dir = out_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "__init__.py").touch(exist_ok=True)
            (src_dir / "workflows.py").write_text(
                emit_workflows_code(spec, sources), encoding="utf-8"
            )
            (src_dir / "cli_workflows.py").write_text(
                emit_arazzo_cli_code(spec), encoding="utf-8"
            )
            (src_dir / "arazzo.snapshot.json").write_text(
                emit_arazzo_json(spec, indent=2), encoding="utf-8"
            )
            if tests:
                test_dir = out_dir / "test"
                test_dir.mkdir(parents=True, exist_ok=True)
                (test_dir / "__init__.py").touch(exist_ok=True)
                (test_dir / "test_workflows.py").write_text(
                    emit_arazzo_tests_code(spec), encoding="utf-8"
                )
        elif subcommand == "to_tests":
            test_dir = out_dir / "test"
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "__init__.py").touch(exist_ok=True)
            (test_dir / "test_workflows.py").write_text(
                emit_arazzo_tests_code(spec), encoding="utf-8"
            )
        else:
            routes_dir = out_dir / "routes"
            routes_dir.mkdir(parents=True, exist_ok=True)
            (routes_dir / "__init__.py").touch(exist_ok=True)
            (routes_dir / "workflows.py").write_text(
                emit_fastapi_arazzo_routes(spec), encoding="utf-8"
            )
            test_dir = out_dir / "tests"
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "__init__.py").touch(exist_ok=True)
            (test_dir / "test_workflows.py").write_text(
                emit_arazzo_tests_code(spec), encoding="utf-8"
            )

    if not no_installable_package:
        scaffold_package(out_dir, is_server=(subcommand == "to_server"))

    if not no_github_actions:
        scaffold_github_actions(out_dir, tests=tests)

    print(f"Successfully generated Arazzo {subcommand} in {out_dir}")


def generate_to_arazzo(input_path: str, output_path: str) -> None:
    """Extract an Arazzo 1.1.0 specification from a Python module or directory.

    Args:
        input_path: Path to a Python file (`workflows.py`, `cli_workflows.py`, `test_workflows.py`) or directory.
        output_path: Output file path for the generated `arazzo.json`.
    """
    if not output_path:
        output_path = "arazzo.json"
    in_path = Path(input_path)
    out_path = Path(output_path)

    if in_path.is_dir():
        for rel_candidate in (
            Path("src") / "workflows.py",
            Path("workflows.py"),
            Path("src") / "cli_workflows.py",
            Path("cli_workflows.py"),
            Path("routes") / "workflows.py",
            Path("test") / "test_workflows.py",
            Path("tests") / "test_workflows.py",
        ):
            target = in_path / rel_candidate
            if target.exists():
                generate_to_arazzo(str(target), str(out_path))
                return
        snapshot = (
            in_path / "src" / "arazzo.snapshot.json"
            if (in_path / "src" / "arazzo.snapshot.json").exists()
            else in_path / "arazzo.snapshot.json"
        )
        spec = parse_arazzo_json(snapshot.read_text(encoding="utf-8"), snapshot.parent)
        out_path.write_text(emit_arazzo_json(spec, indent=2), encoding="utf-8")
        print(f"Successfully extracted Arazzo spec to {out_path}")
        return

    code = in_path.read_text(encoding="utf-8")
    if "__arazzo_cli_spec__" in code or ("argparse" in code and "add_parser" in code):
        spec = extract_arazzo_from_cli_code(code)
    elif "__arazzo_server_spec__" in code or "APIRouter" in code:
        spec = extract_arazzo_from_fastapi_code(code)
    elif "__arazzo_test_spec__" in code or "def test_" in code:
        spec = extract_arazzo_from_test_code(code)
    else:
        spec = extract_arazzo_from_code(code)

    out_path.write_text(emit_arazzo_json(spec, indent=2), encoding="utf-8")
    print(f"Successfully extracted Arazzo spec to {out_path}")


def generate_to_openapi(input_path: str | Path, output_path: str | Path) -> None:
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
                info=Info(title="Extracted API", version="0.0.4"),
                paths={},
                components=Components(schemas={}),
            )

        client_py = in_path / "src" / "client.py"
        if not client_py.exists():
            client_py = in_path / "client.py"

        models_py = in_path / "src" / "models.py"
        if not models_py.exists():
            models_py = in_path / "models.py"

        models_dir = (
            in_path / "src" / "models"
            if (in_path / "src" / "models").is_dir()
            else in_path / "models"
        )

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

        if models_py.is_file():
            mod = cst.parse_module(models_py.read_text(encoding="utf-8"))
            parse_sqlalchemy_cdd(mod, spec)

        if models_dir.is_dir():
            for sa_file in sorted(models_dir.glob("*.py")):
                if sa_file.name != "__init__.py":
                    mod = cst.parse_module(sa_file.read_text(encoding="utf-8"))
                    parse_sqlalchemy_cdd(mod, spec)

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
            info=Info(title="Extracted API", version="0.0.4"),
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
        p.add_argument(
            "--arazzo",
            type=str,
            default=None,
            help="Optional companion Arazzo 1.1.0 specification to bundle.",
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

    from_arazzo_parser = subparsers.add_parser(
        "from_arazzo", help="Generate code from an Arazzo 1.1.0 specification."
    )
    from_arazzo_subparsers = from_arazzo_parser.add_subparsers(
        dest="from_arazzo_command", required=True
    )
    for ar_subcmd in ["to_sdk", "to_sdk_cli", "to_server", "to_tests"]:
        ar_p = from_arazzo_subparsers.add_parser(
            ar_subcmd,
            help=f"Generate {ar_subcmd} artifacts from an Arazzo 1.1.0 specification.",
        )
        ar_group = ar_p.add_mutually_exclusive_group(required=False)
        ar_group.add_argument(
            "-i",
            "-f",
            "--input",
            type=str,
            help="Path to the Arazzo 1.1.0 specification.",
        )
        ar_group.add_argument(
            "-d",
            "--input-dir",
            type=str,
            help="Directory containing Arazzo specifications.",
        )
        ar_p.add_argument(
            "-o",
            "--output",
            type=str,
            default=".",
            help="Output file or directory path.",
        )
        ar_p.add_argument(
            "--no-github-actions",
            action="store_true",
            help="Do not generate GitHub Actions scaffolding.",
        )
        ar_p.add_argument(
            "--no-installable-package",
            action="store_true",
            help="Do not generate installable package scaffolding.",
        )
        ar_p.add_argument(
            "--tests",
            action="store_true",
            help="Generate workflow end-to-end tests.",
        )

    to_arazzo_parser = subparsers.add_parser(
        "to_arazzo",
        help="Parse Python workflow code and extract an Arazzo 1.1.0 specification.",
    )
    to_arazzo_parser.add_argument(
        "-i",
        "-f",
        "--input",
        type=str,
        required=True,
        help="Path to Python workflow file or directory.",
    )
    to_arazzo_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="arazzo.json",
        help="Output file path for the generated Arazzo specification.",
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
        choices=["class", "sqlalchemy", "function", "openapi", "arazzo", "workflow"],
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
        "-l", "--listen", type=str, default="127.0.0.1", help="Address to listen on"
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
            getattr(args, "arazzo", None),
        )
    elif args.command == "to_openapi":
        in_path = args.input
        generate_to_openapi(in_path, args.output)
    elif args.command == "from_arazzo":
        ar_cmd = args.from_arazzo_command
        if not args.input and not getattr(args, "input_dir", None):
            from_arazzo_parser.print_help()
            sys.exit(1)
        generate_from_arazzo(
            ar_cmd,
            args.input,
            getattr(args, "input_dir", None),
            args.output,
            args.no_github_actions,
            args.no_installable_package,
            getattr(args, "tests", False),
        )
    elif args.command == "to_arazzo":
        generate_to_arazzo(args.input, args.output)
    elif args.command == "to_docs_json":
        generate_docs_json(args.input, args.no_imports, args.no_wrapping, args.output)
    elif args.command == "serve_json_rpc":
        serve_json_rpc(args.port, args.listen)
    elif args.command == "mcp":
        run_mcp_server()


if __name__ == "__main__":  # pragma: no cover
    main()
