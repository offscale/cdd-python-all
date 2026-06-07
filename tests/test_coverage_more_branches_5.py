"""Tests for test_coverage_more_branches_5.py."""

import libcst as cst
from openapi_client.docstrings.parse import parse_docstring


def test_docstring_empty_body():
    # 20->36
    """Test test_docstring_empty_body."""
    node = cst.FunctionDef(
        name=cst.Name("test"), params=cst.Parameters(), body=cst.IndentedBlock(body=[])
    )
    assert parse_docstring(node) == (None, None)


def test_docstring_empty_string():
    # 28->36
    """Test test_docstring_empty_string."""
    node = cst.FunctionDef(
        name=cst.Name("test"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString("''"))])
            ]
        ),
    )
    assert parse_docstring(node) == (None, None)
