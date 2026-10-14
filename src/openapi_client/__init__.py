"""OpenAPI Python Client (CDD) Library."""

from __future__ import annotations

from openapi_client import mcp
from openapi_client.models import OpenAPI
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.sdk import (
    generate_docs_json,
    generate_from_openapi,
    generate_to_openapi,
    run_sync,
    serve_json_rpc,
)

__all__ = [
    "ClientGenerator",
    "OpenAPI",
    "extract_from_code",
    "generate_docs_json",
    "generate_from_openapi",
    "generate_to_openapi",
    "mcp",
    "run_sync",
    "serve_json_rpc",
]
