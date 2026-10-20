"""Programmatic SDK for cdd-python-all."""

from __future__ import annotations

from typing import Any


def cli_generate_from_openapi(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.generate_from_openapi`.

    Args:
        *args: Positional arguments forwarded to `cli.generate_from_openapi`.
        **kwargs: Keyword arguments forwarded to `cli.generate_from_openapi`.
    """
    from openapi_client import cli as _cli

    _cli.generate_from_openapi(*args, **kwargs)


def cli_generate_to_openapi(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.generate_to_openapi`.

    Args:
        *args: Positional arguments forwarded to `cli.generate_to_openapi`.
        **kwargs: Keyword arguments forwarded to `cli.generate_to_openapi`.
    """
    from openapi_client import cli as _cli

    _cli.generate_to_openapi(*args, **kwargs)


def cli_generate_from_arazzo(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.generate_from_arazzo`.

    Args:
        *args: Positional arguments forwarded to `cli.generate_from_arazzo`.
        **kwargs: Keyword arguments forwarded to `cli.generate_from_arazzo`.
    """
    from openapi_client import cli as _cli

    _cli.generate_from_arazzo(*args, **kwargs)


def cli_generate_to_arazzo(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.generate_to_arazzo`.

    Args:
        *args: Positional arguments forwarded to `cli.generate_to_arazzo`.
        **kwargs: Keyword arguments forwarded to `cli.generate_to_arazzo`.
    """
    from openapi_client import cli as _cli

    _cli.generate_to_arazzo(*args, **kwargs)


def cli_generate_docs_json(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.generate_docs_json`.

    Args:
        *args: Positional arguments forwarded to `cli.generate_docs_json`.
        **kwargs: Keyword arguments forwarded to `cli.generate_docs_json`.
    """
    from openapi_client import cli as _cli

    _cli.generate_docs_json(*args, **kwargs)


def cli_serve_json_rpc(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.serve_json_rpc`.

    Args:
        *args: Positional arguments forwarded to `cli.serve_json_rpc`.
        **kwargs: Keyword arguments forwarded to `cli.serve_json_rpc`.
    """
    from openapi_client import cli as _cli

    _cli.serve_json_rpc(*args, **kwargs)


def cli_sync_dir(*args: Any, **kwargs: Any) -> None:
    """Delegate to `cli.sync_dir`.

    Args:
        *args: Positional arguments forwarded to `cli.sync_dir`.
        **kwargs: Keyword arguments forwarded to `cli.sync_dir`.
    """
    from openapi_client import cli as _cli

    _cli.sync_dir(*args, **kwargs)


def cli_run_mcp_server() -> None:
    """Delegate to `cli.run_mcp_server`."""
    from openapi_client import cli as _cli

    _cli.run_mcp_server()


def generate_from_openapi(
    input_path: str | None = None,
    output_dir: str = ".",
    no_github_actions: bool = False,
    no_installable_package: bool = False,
    tests: bool = False,
    subcommand: str = "to_sdk",
) -> None:
    """Generate code from an OpenAPI specification.

    Args:
        input_path: Path to the OpenAPI JSON file.
        output_dir: Target directory for generated artifacts.
        no_github_actions: If True, skip GitHub Actions CI scaffolding.
        no_installable_package: If True, skip `pyproject.toml` scaffolding.
        tests: If True, generate unit tests and mock server.
        subcommand: Generation target (`'to_sdk'`, `'to_sdk_cli'`, or `'to_server'`).
    """
    cli_generate_from_openapi(
        subcommand=subcommand,
        input_path=input_path,
        input_dir=None,
        output_dir=output_dir,
        no_github_actions=no_github_actions,
        no_installable_package=no_installable_package,
        tests=tests,
    )


def generate_to_openapi(input_dir: str = ".", output_path: str | None = None) -> None:
    """Generate an OpenAPI specification from source code.

    Args:
        input_dir: Path to the source directory or file.
        output_path: Output file path for the generated `openapi.json`.
    """
    cli_generate_to_openapi(input_dir, output_path or "openapi.json")


def generate_from_arazzo(
    input_path: str | None = None,
    output_dir: str = ".",
    no_github_actions: bool = False,
    no_installable_package: bool = False,
    tests: bool = False,
    subcommand: str = "to_sdk",
) -> None:
    """Generate Python workflows, CLI, server routes, or tests from an Arazzo 1.1.0 specification.

    Args:
        input_path: Path to the Arazzo 1.1.0 JSON file.
        output_dir: Target directory for generated artifacts.
        no_github_actions: If True, skip GitHub Actions CI scaffolding.
        no_installable_package: If True, skip `pyproject.toml` scaffolding.
        tests: If True, generate end-to-end workflow test suites.
        subcommand: Generation target (`'to_sdk'`, `'to_sdk_cli'`, `'to_server'`, or `'to_tests'`).
    """
    cli_generate_from_arazzo(
        subcommand=subcommand,
        input_path=input_path,
        input_dir=None,
        output_dir=output_dir,
        no_github_actions=no_github_actions,
        no_installable_package=no_installable_package,
        tests=tests,
    )


def generate_to_arazzo(input_dir: str = ".", output_path: str | None = None) -> None:
    """Generate an Arazzo 1.1.0 specification from Python workflow source code.

    Args:
        input_dir: Path to the workflow source file or directory.
        output_path: Output file path for the generated `arazzo.json`.
    """
    cli_generate_to_arazzo(input_dir, output_path or "arazzo.json")


def generate_docs_json(
    input_path: str = "",
    no_imports: bool = False,
    no_wrapping: bool = False,
    output_path: str | None = None,
) -> None:
    """Generate JSON documentation with code snippets for an OpenAPI specification.

    Args:
        input_path: Path or URL to the OpenAPI specification.
        no_imports: If True, omit import statements in generated snippets.
        no_wrapping: If True, omit `main()` wrapper in generated snippets.
        output_path: Optional file path to save the generated JSON documentation.
    """
    cli_generate_docs_json(input_path, no_imports, no_wrapping, output_path)


def serve_json_rpc(port: int = 8080, listen: str = "127.0.0.1") -> None:
    """Expose CLI interface as a JSON-RPC server.

    Args:
        port: Port to listen on.
        listen: Host address to bind to.
    """
    cli_serve_json_rpc(port, listen)


def run_sync(
    input_dir: str = ".",
    truth: str | None = None,
    output_dir: str | None = None,
) -> None:
    """Sync a directory containing client.py, mock_server.py, test_client.py, cli_main.py.

    Args:
        input_dir: Directory containing source files and/or `openapi.json`.
        truth: Optional source of truth (`'openapi'`, `'class'`, `'function'`, `'sqlalchemy'`).
        output_dir: Optional output directory.
    """
    if truth is None and output_dir is None:
        cli_sync_dir(input_dir)
    else:
        cli_sync_dir(input_dir, truth, output_dir)


def mcp() -> None:
    """Run an MCP server exposing generator commands over stdio."""
    cli_run_mcp_server()
