"""
Module for emitting pytest tests from OpenAPI examples.
"""

from typing import List
import libcst as cst
from openapi_client.models import OpenAPI, Operation


def emit_operation_test(
    method: str, path: str, operation: Operation
) -> cst.FunctionDef:
    """
    Emit a pytest unit test for an API operation.
    """
    func_name = f"test_{operation.operationId or method + '_' + path.replace('/', '_').strip('_')}"

    body = [
        # Example test body: client = Client("http://localhost")
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(cst.Name("client"))],
                    value=cst.Call(
                        func=cst.Name("Client"),
                        args=[cst.Arg(cst.SimpleString('"http://localhost"'))],
                    ),
                )
            ]
        ),
        cst.SimpleStatementLine([cst.Pass()]),
    ]

    return cst.FunctionDef(
        name=cst.Name(func_name),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=body),
    )


def emit_tests(spec: OpenAPI) -> cst.Module:
    """
    Emit a pytest test module for the OpenAPI spec.
    """
    body: List[cst.SimpleStatementLine | cst.BaseCompoundStatement | cst.EmptyLine] = []

    body.append(
        cst.SimpleStatementLine(
            [cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])]
        )
    )
    body.append(
        cst.SimpleStatementLine(
            [
                cst.ImportFrom(
                    module=cst.Name("openapi_client"),
                    names=[cst.ImportAlias(name=cst.Name("Client"))],
                )
            ]
        )
    )
    body.append(cst.EmptyLine())

    if spec.paths:
        for path, path_item in spec.paths.items():
            if path.startswith("/"):
                for method in ["get", "post", "put", "delete", "patch"]:
                    operation = getattr(path_item, method, None)
                    if operation:
                        body.append(emit_operation_test(method, path, operation))
                        body.append(cst.EmptyLine())

    return cst.Module(body=body)  # type: ignore[arg-type]
