import libcst as cst
from openapi_client.docstrings.parse import parse_docstring


def test_docstring_empty_body():
    # 20->36
    node = cst.FunctionDef(
        name=cst.Name("test"), params=cst.Parameters(), body=cst.IndentedBlock(body=[])
    )
    assert parse_docstring(node) == (None, None)


def test_docstring_empty_string():
    # 28->36
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
