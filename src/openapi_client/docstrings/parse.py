"""
Module for parsing docstrings to extract OpenAPI description details.
"""

from typing import Optional, Tuple
import libcst as cst


def parse_docstring(
    node: cst.FunctionDef | cst.ClassDef,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts summary and description from a function or class docstring.

    Returns:
        Tuple[Optional[str], Optional[str]]: (summary, description)
    """
    if isinstance(node.body, cst.IndentedBlock):
        if node.body.body:
            first_stmt = node.body.body[0]
            if isinstance(first_stmt, cst.SimpleStatementLine) and first_stmt.body:
                first_expr = first_stmt.body[0]
                if isinstance(first_expr, cst.Expr) and isinstance(
                    first_expr.value, cst.SimpleString
                ):
                    doc_val = first_expr.value.evaluated_value
                    if doc_val:
                        import re

                        doc_val = str(doc_val).strip("'\"").strip()
                        parts = re.split(r"\n\s*\n", doc_val, maxsplit=1)
                        summary = parts[0].strip() if parts else None
                        description = parts[1].strip() if len(parts) > 1 else None
                        return summary, description
    return None, None
