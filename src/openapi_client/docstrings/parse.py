"""Module for parsing docstrings to extract OpenAPI description details."""

from __future__ import annotations

import re

import libcst as cst


def parse_docstring(
    node: cst.FunctionDef | cst.ClassDef,
) -> tuple[str | None, str | None]:
    """Extract summary and description from a function or class docstring.

    Args:
        node: The LibCST FunctionDef or ClassDef node to inspect.

    Returns:
        A tuple of `(summary, description)`, where either element may be None.
    """
    if isinstance(node.body, cst.IndentedBlock) and node.body.body:
        first_stmt = node.body.body[0]
        if isinstance(first_stmt, cst.SimpleStatementLine) and first_stmt.body:
            first_expr = first_stmt.body[0]
            if isinstance(first_expr, cst.Expr) and isinstance(
                first_expr.value, cst.SimpleString
            ):
                doc_val = first_expr.value.evaluated_value
                if doc_val:
                    doc_str = str(doc_val).strip("'\"").strip()
                    parts = re.split(r"\n\s*\n", doc_str, maxsplit=1)
                    summary = parts[0].strip() if parts else None
                    description = parts[1].strip() if len(parts) > 1 else None
                    return summary, description
    return None, None
