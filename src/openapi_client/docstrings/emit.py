"""Module for emitting docstrings for generated Python models and methods."""

from __future__ import annotations

import libcst as cst

from openapi_client.models import Operation, Schema


def emit_class_docstring(schema: Schema) -> cst.SimpleStatementLine | None:
    """Generate a docstring statement for a Pydantic model.

    Args:
        schema: The OpenAPI Schema object.

    Returns:
        A LibCST SimpleStatementLine containing the docstring, or None if empty.
    """
    desc = getattr(schema, "description", None)
    summary = getattr(schema, "summary", None)

    parts = []
    if summary:
        parts.append(summary)
    if desc:
        parts.append(desc)

    if parts:
        doc = "\\n\\n".join(parts)
        return cst.SimpleStatementLine(
            [cst.Expr(value=cst.SimpleString(f'"""{doc}"""'))]
        )
    return None


def emit_function_docstring(operation: Operation) -> cst.SimpleStatementLine | None:
    """Generate a docstring statement for an API client method.

    Args:
        operation: The OpenAPI Operation object.

    Returns:
        A LibCST SimpleStatementLine containing the docstring, or None if empty.
    """
    desc = getattr(operation, "description", None)
    summary = getattr(operation, "summary", None)

    parts = []
    if summary:
        parts.append(summary)
    if desc:
        parts.append(desc)

    if parts:
        doc = "\\n\\n".join(parts)
        return cst.SimpleStatementLine(
            [cst.Expr(value=cst.SimpleString(f'"""{doc}"""'))]
        )
    return None
