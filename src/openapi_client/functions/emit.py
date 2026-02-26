"""
Module for emitting Python functions (API client methods) from OpenAPI paths.
"""

from typing import Dict, List, Optional
import libcst as cst
from openapi_client.models import OpenAPI, PathItem, Operation


def emit_function(method: str, path: str, operation: Operation) -> cst.FunctionDef:
    """
    Emit an HTTP client method for a given OpenAPI operation.

    Args:
        method (str): HTTP method (e.g., 'get', 'post').
        path (str): The route path.
        operation (Operation): The OpenAPI Operation object containing parameters and body info.

    Returns:
        cst.FunctionDef: The generated AST node for the method.
    """
    params_list = [cst.Param(name=cst.Name("self"))]

    from openapi_client.docstrings.emit import emit_function_docstring

    docstring = emit_function_docstring(operation)

    body_statements = []
    if docstring:
        body_statements.append(docstring)

    # Process query, header, path, cookie parameters
    if operation.parameters:
        for param in operation.parameters:
            if hasattr(param, "name"):
                param_name = param.name.replace("-", "_")
                params_list.append(
                    cst.Param(
                        name=cst.Name(param_name),
                        annotation=cst.Annotation(cst.Name("Any")),
                    )
                )

    # Build the method body
    body_statements.extend(
        [
            # Build URL (needs actual path variable interpolation later)
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("url"))],
                        value=cst.BinaryOperation(
                            left=cst.Attribute(
                                value=cst.Name("self"), attr=cst.Name("base_url")
                            ),
                            operator=cst.Add(),
                            right=cst.SimpleString(f'"{path}"'),
                        ),
                    )
                ]
            ),
            # Perform HTTP request
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("response"))],
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name("http")
                                ),
                                attr=cst.Name("request"),
                            ),
                            args=[
                                cst.Arg(value=cst.SimpleString(f'"{method.upper()}"')),
                                cst.Arg(value=cst.Name("url")),
                            ],
                        ),
                    )
                ]
            ),
            cst.SimpleStatementLine([cst.Return(value=cst.Name("response"))]),
        ]
    )

    req_body = cst.IndentedBlock(body=body_statements)

    # Use the operationId as the method name if present, else synthesize
    operation_id = (
        operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
    )
    return cst.FunctionDef(
        name=cst.Name(operation_id),
        params=cst.Parameters(params=params_list),
        body=req_body,
    )


def emit_functions(spec: OpenAPI) -> List[cst.FunctionDef]:
    """
    Emit a list of HTTP client methods for all paths in an OpenAPI spec.

    Args:
        spec (OpenAPI): The parsed OpenAPI specification.

    Returns:
        List[cst.FunctionDef]: A list of generated AST nodes for the methods.
    """
    methods = []

    # Generate __init__
    init_params = cst.Parameters(
        params=[
            cst.Param(name=cst.Name("self")),
            cst.Param(
                name=cst.Name("base_url"), annotation=cst.Annotation(cst.Name("str"))
            ),
        ]
    )
    init_body = cst.IndentedBlock(
        body=[
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name("base_url")
                                )
                            )
                        ],
                        value=cst.Name("base_url"),
                    )
                ]
            ),
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[
                            cst.AssignTarget(
                                cst.Attribute(
                                    value=cst.Name("self"), attr=cst.Name("http")
                                )
                            )
                        ],
                        value=cst.Call(func=cst.Name("PoolManager")),
                    )
                ]
            ),
        ]
    )
    methods.append(
        cst.FunctionDef(name=cst.Name("__init__"), params=init_params, body=init_body)
    )

    if spec.paths:
        for path, path_item in spec.paths.items():
            if path.startswith("/"):
                for method in ["get", "post", "put", "delete", "patch"]:
                    operation = getattr(path_item, method, None)
                    if operation:
                        methods.append(emit_function(method, path, operation))

    return methods
