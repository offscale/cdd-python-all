"""
Module for emitting docstrings for generated Python models and methods.
"""

from typing import Optional
import libcst as cst
from openapi_client.models import Schema, Operation


def emit_class_docstring(schema: Schema) -> Optional[cst.SimpleStatementLine]:
    """
    Generate a docstring for a Pydantic model.
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


def emit_function_docstring(operation: Operation) -> Optional[cst.SimpleStatementLine]:
    """
    Generate a docstring for an API client method.
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
