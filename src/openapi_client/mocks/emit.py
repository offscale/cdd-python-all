"""
Module for generating API mock servers based on OpenAPI specs.
"""

from typing import List
import libcst as cst
from openapi_client.models import OpenAPI


def emit_mock_server(spec: OpenAPI) -> cst.Module:
    """
    Emit a basic mock server using a simple framework (e.g. FastAPI/Flask)
    based on the operations defined in the OpenAPI spec.
    """
    body: List[cst.SimpleStatementLine | cst.BaseCompoundStatement | cst.EmptyLine] = []

    # Simple placeholder: emit an empty server setup
    body.append(
        cst.SimpleStatementLine(
            [
                cst.ImportFrom(
                    module=cst.Name("fastapi"),
                    names=[cst.ImportAlias(name=cst.Name("FastAPI"))],
                )
            ]
        )
    )
    body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(cst.Name("app"))],
                    value=cst.Call(func=cst.Name("FastAPI")),
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
                        # Emitting a route
                        # @app.get("/path")
                        # def route_name():
                        #     pass
                        route_name = (
                            operation.operationId
                            or f"{method}_{path.replace('/', '_').strip('_')}"
                        )
                        decorator = cst.Decorator(
                            decorator=cst.Call(
                                func=cst.Attribute(
                                    value=cst.Name("app"), attr=cst.Name(method)
                                ),
                                args=[cst.Arg(cst.SimpleString(f'"{path}"'))],
                            )
                        )
                        func = cst.FunctionDef(
                            name=cst.Name(route_name),
                            params=cst.Parameters(),
                            body=cst.IndentedBlock(
                                [cst.SimpleStatementLine([cst.Pass()])]
                            ),
                            decorators=[decorator],
                        )
                        body.append(func)
                        body.append(cst.EmptyLine())

    return cst.Module(body=body)  # type: ignore[arg-type]
