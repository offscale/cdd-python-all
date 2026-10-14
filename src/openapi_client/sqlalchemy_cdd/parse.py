"""SQLAlchemy CDD code parsing module."""

from __future__ import annotations

import libcst as cst

from openapi_client.classes.parse import extract_classes_from_ast
from openapi_client.models import OpenAPI


def parse_sqlalchemy_cdd(module: cst.Module, spec: OpenAPI) -> None:
    """Parse SQLAlchemy CDD code into OpenAPI component schemas.

    Args:
        module: The parsed LibCST Module node.
        spec: The OpenAPI specification to update.
    """
    extract_classes_from_ast(module, spec)
