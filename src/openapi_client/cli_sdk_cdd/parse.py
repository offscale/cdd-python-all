"""CLI SDK CDD code parsing module."""

from __future__ import annotations

import libcst as cst

from openapi_client.cli_sdk.parse import extract_cli_from_ast
from openapi_client.models import OpenAPI


def parse_cli_sdk_cdd(module: cst.Module, spec: OpenAPI) -> None:
    """Parse CLI SDK CDD code and update the OpenAPI specification.

    Args:
        module: The parsed LibCST Module node.
        spec: The OpenAPI specification to update.
    """
    extract_cli_from_ast(module, spec)
