"""Module for generating API mock servers based on OpenAPI specs."""

from __future__ import annotations

import libcst as cst

from openapi_client.functions.utils import sanitize_name
from openapi_client.models import OpenAPI


def emit_mock_server(spec: OpenAPI) -> cst.Module:
    """Emit a basic FastAPI mock server based on the operations defined in the OpenAPI spec.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated LibCST Module node for the mock server.
    """
    body: list[cst.BaseStatement | cst.EmptyLine] = []

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
                        raw_route_name = (
                            operation.operationId
                            or f"{method}_{path.replace('/', '_').strip('_')}"
                        )
                        route_name = sanitize_name(raw_route_name)
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

    return cst.Module(body=body)
