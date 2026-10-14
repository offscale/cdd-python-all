"""Module for extracting an OpenAPI specification from Python client code."""

from __future__ import annotations

import libcst as cst

from openapi_client.classes.parse import extract_classes_from_ast
from openapi_client.functions.parse import extract_functions_from_ast
from openapi_client.models import Components, Info, OpenAPI


def extract_from_code(code: str) -> OpenAPI:
    """Extract a complete OpenAPI specification from a Python client module.

    Args:
        code: The Python source code string.

    Returns:
        The extracted OpenAPI specification.
    """
    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Extracted API", version="0.0.3"),
        paths={},
        components=Components(schemas={}),
    )

    module = cst.parse_module(code)

    extract_classes_from_ast(module, spec)
    extract_functions_from_ast(module, spec)

    return spec
