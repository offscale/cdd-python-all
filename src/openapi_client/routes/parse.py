"""
Module for extracting an OpenAPI specification from Python client code.
"""

import libcst as cst
from openapi_client.models import OpenAPI, Info, Components
from openapi_client.functions.parse import extract_functions_from_ast
from openapi_client.classes.parse import extract_classes_from_ast


def extract_from_code(code: str) -> OpenAPI:
    """
    Extract a complete OpenAPI specification from a Python client module.

    Args:
        code (str): The Python source code.

    Returns:
        OpenAPI: The extracted OpenAPI specification.
    """
    spec = OpenAPI(
        **{
            "openapi": "3.2.0",
            "info": Info(title="Extracted API", version="0.0.1"),
            "paths": {},
            "components": Components(schemas={}),
        }
    )  # type: ignore

    module = cst.parse_module(code)

    # Extract classes (schemas)
    extract_classes_from_ast(module, spec)

    # Extract functions (operations)
    extract_functions_from_ast(module, spec)

    return spec
