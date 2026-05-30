"""Programmatic SDK for cdd-python-all."""

from typing import Optional
from openapi_client.cli import generate_from_openapi as cli_generate_from_openapi
from openapi_client.cli import generate_to_openapi as cli_generate_to_openapi
from openapi_client.cli import generate_docs_json as cli_generate_docs_json
from openapi_client.cli import serve_json_rpc as cli_serve_json_rpc


def generate_from_openapi(
    input_path: str,
    output_dir: str,
    no_github_actions: bool = False,
    no_installable_package: bool = False,
    tests: bool = False,
    subcommand: str = "to_sdk",
) -> None:
    """Generate code from an OpenAPI specification."""
    cli_generate_from_openapi(
        subcommand=subcommand,
        input_path=input_path,
        output_dir=output_dir,
        no_github_actions=no_github_actions,
        no_installable_package=no_installable_package,
        tests=tests,
    )


def generate_to_openapi(input_dir: str, output_path: Optional[str] = None) -> None:
    """Generate an OpenAPI specification from source code."""
    cli_generate_to_openapi(input_dir, output_path)


def generate_docs_json(
    input_path: str,
    no_imports: bool = False,
    no_wrapping: bool = False,
    output_path: Optional[str] = None,
) -> None:
    """Generate JSON documentation with code snippets for an OpenAPI specification."""
    cli_generate_docs_json(input_path, no_imports, no_wrapping, output_path)


def serve_json_rpc(port: int = 8080, listen: str = "127.0.0.1") -> None:
    """Expose CLI interface as a JSON-RPC server."""
    cli_serve_json_rpc(port, listen)
