"""Module for emitting Python functions (API client methods) from OpenAPI paths."""

from __future__ import annotations

import re as _re

import libcst as cst
from openapi_client.docstrings.emit import emit_function_docstring
from openapi_client.functions.utils import (
    get_annotation_for_schema,
    safe_param_name,
    sanitize_name,
)
from openapi_client.models import OpenAPI, Operation
from openapi_client.openapi.keywords import HTTP_METHODS


def _safe_param_name(raw_name: str) -> str:
    """Sanitize a parameter name while preserving valid camelCase identifiers.

    Args:
        raw_name: Raw parameter name from OpenAPI.

    Returns:
        A valid non-keyword Python identifier string.
    """
    return safe_param_name(raw_name)


def emit_function(method: str, path: str, operation: Operation) -> cst.FunctionDef:
    """Emit an HTTP client method for a given OpenAPI operation.

    Args:
        method: HTTP method (e.g., `'get'`, `'post'`).
        path: The route path string.
        operation: The OpenAPI Operation object containing parameters and body info.

    Returns:
        The generated LibCST FunctionDef node for the method.
    """
    params_list = [cst.Param(name=cst.Name("self"))]
    required_params: list[cst.Param] = []
    optional_params: list[cst.Param] = []

    docstring = emit_function_docstring(operation)

    body_statements: list[cst.BaseStatement] = []
    if docstring:
        body_statements.append(docstring)

    query_statements: list[cst.BaseStatement] = []
    has_query = False
    has_body_param = False
    body_param_name = "body"
    has_form_data = False
    form_data_params: list[tuple[str, str]] = []

    if operation.parameters:
        for p in operation.parameters:
            if getattr(p, "in_", getattr(p, "in", None)) == "body":
                has_body_param = True
                if hasattr(p, "name"):
                    body_param_name = _safe_param_name(p.name)

        has_query_params = any(getattr(p, "in_", getattr(p, "in", None)) == "query" for p in operation.parameters)
        if has_query_params:
            query_statements.append(
                cst.SimpleStatementLine(
                    [
                        cst.Assign(
                            targets=[cst.AssignTarget(cst.Name("query_params"))],
                            value=cst.List(elements=[]),
                        )
                    ]
                )
            )
            has_query = True

        for param in operation.parameters:
            if hasattr(param, "name"):
                param_name = _safe_param_name(param.name)

                schema_obj = getattr(param, "schema_", getattr(param, "schema", None))
                annotation_str = get_annotation_for_schema(schema_obj)

                if annotation_str.startswith(("list", "dict")) or "|" in annotation_str or "." in annotation_str:
                    ann_node = cst.parse_expression(annotation_str)
                else:
                    ann_node = cst.Name(annotation_str)

                param_default = getattr(param, "default", None)
                if param_default is None and schema_obj is not None:
                    param_default = getattr(schema_obj, "default", None)
                if param_default is not None:
                    optional_params.append(
                        cst.Param(
                            name=cst.Name(param_name),
                            annotation=cst.Annotation(ann_node),
                            default=cst.Name("None"),
                        )
                    )
                else:
                    required_params.append(
                        cst.Param(
                            name=cst.Name(param_name),
                            annotation=cst.Annotation(ann_node),
                        )
                    )

                p_in = getattr(param, "in_", getattr(param, "in", None))
                if p_in in ("formData", "form"):
                    has_form_data = True
                    form_data_params.append((param.name, param_name))

                if p_in == "query":
                    style = getattr(param, "style", "form")
                    delim = " " if style == "spaceDelimited" else ("|" if style == "pipeDelimited" else ",")

                    if style in ("spaceDelimited", "pipeDelimited"):
                        query_statements.append(
                            cst.If(
                                test=cst.Name(param_name),
                                body=cst.IndentedBlock(
                                    body=[
                                        cst.SimpleStatementLine(
                                            [
                                                cst.Expr(
                                                    value=cst.Call(
                                                        func=cst.Attribute(
                                                            value=cst.Name("query_params"),
                                                            attr=cst.Name("append"),
                                                        ),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.BinaryOperation(
                                                                    left=cst.SimpleString(f"'{param.name}='"),
                                                                    operator=cst.Add(),
                                                                    right=cst.Call(
                                                                        func=cst.Attribute(
                                                                            value=cst.SimpleString(f"'{delim}'"),
                                                                            attr=cst.Name("join"),
                                                                        ),
                                                                        args=[cst.Arg(value=cst.Name(param_name))],
                                                                    ),
                                                                )
                                                            )
                                                        ],
                                                    )
                                                )
                                            ]
                                        )
                                    ]
                                ),
                            )
                        )
                    else:
                        query_statements.append(
                            cst.If(
                                test=cst.Name(param_name),
                                body=cst.IndentedBlock(
                                    body=[
                                        cst.SimpleStatementLine(
                                            [
                                                cst.Expr(
                                                    value=cst.Call(
                                                        func=cst.Attribute(
                                                            value=cst.Name("query_params"),
                                                            attr=cst.Name("append"),
                                                        ),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.BinaryOperation(
                                                                    left=cst.SimpleString(f"'{param.name}='"),
                                                                    operator=cst.Add(),
                                                                    right=cst.Call(
                                                                        func=cst.Name("str"),
                                                                        args=[cst.Arg(value=cst.Name(param_name))],
                                                                    ),
                                                                )
                                                            )
                                                        ],
                                                    )
                                                )
                                            ]
                                        )
                                    ]
                                ),
                            )
                        )

    if operation.requestBody and not has_body_param:
        optional_params.append(
            cst.Param(
                name=cst.Name("body"),
                annotation=cst.Annotation(cst.Name("dict")),
                default=cst.Name("None"),
            )
        )
    params_list.extend(required_params)
    params_list.extend(optional_params)
    body_statements.extend(query_statements)

    if "{" in path and "}" in path:
        safe_path = _re.sub(r"\{([^}]+)\}", lambda m: "{" + _safe_param_name(m.group(1)) + "}", path)
        url_value = cst.parse_expression(f'self.base_url + f"{safe_path}"')
    else:
        url_value = cst.BinaryOperation(
            left=cst.Attribute(value=cst.Name("self"), attr=cst.Name("base_url")),
            operator=cst.Add(),
            right=cst.SimpleString(f'"{path}"'),
        )
    if has_query:
        url_value = cst.BinaryOperation(
            left=url_value,
            operator=cst.Add(),
            right=cst.IfExp(
                test=cst.Name("query_params"),
                body=cst.BinaryOperation(
                    left=cst.SimpleString("'?'"),
                    operator=cst.Add(),
                    right=cst.Call(
                        func=cst.Attribute(value=cst.SimpleString("'&'"), attr=cst.Name("join")),
                        args=[cst.Arg(value=cst.Name("query_params"))],
                    ),
                ),
                orelse=cst.SimpleString('""'),
            ),
        )

    body_statements.extend(
        [
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("url"))],
                        value=url_value,
                    )
                ]
            ),
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("response"))],
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("http")),
                                attr=cst.Name("request"),
                            ),
                            args=[
                                cst.Arg(value=cst.SimpleString(f'"{method.upper()}"')),
                                cst.Arg(value=cst.Name("url")),
                                cst.Arg(
                                    keyword=cst.Name("headers"),
                                    value=cst.IfExp(
                                        test=cst.Attribute(
                                            value=cst.Name("self"),
                                            attr=cst.Name("api_key"),
                                        ),
                                        body=cst.Dict(
                                            elements=[
                                                cst.DictElement(
                                                    key=cst.SimpleString('"api_key"'),
                                                    value=cst.Attribute(
                                                        value=cst.Name("self"),
                                                        attr=cst.Name("api_key"),
                                                    ),
                                                ),
                                                cst.DictElement(
                                                    key=cst.SimpleString('"Authorization"'),
                                                    value=cst.BinaryOperation(
                                                        left=cst.SimpleString('"Bearer "'),
                                                        operator=cst.Add(),
                                                        right=cst.Attribute(
                                                            value=cst.Name("self"),
                                                            attr=cst.Name("api_key"),
                                                        ),
                                                    ),
                                                ),
                                            ]
                                        ),
                                        orelse=cst.Dict(elements=[]),
                                    ),
                                ),
                            ]
                            + (
                                [
                                    cst.Arg(
                                        keyword=cst.Name("json"),
                                        value=cst.Name(body_param_name),
                                    )
                                ]
                                if operation.requestBody or has_body_param
                                else (
                                    [
                                        cst.Arg(
                                            keyword=cst.Name("fields"),
                                            value=cst.Dict(
                                                elements=[
                                                    cst.DictElement(
                                                        key=cst.SimpleString(f'"{k}"'),
                                                        value=cst.Name(v),
                                                    )
                                                    for k, v in form_data_params
                                                ]
                                            ),
                                        )
                                    ]
                                    if has_form_data
                                    else []
                                )
                            ),
                        ),
                    )
                ]
            ),
            cst.SimpleStatementLine([cst.Return(value=cst.Name("response"))]),
        ]
    )

    req_body = cst.IndentedBlock(body=body_statements)

    raw_op_id = operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
    operation_id = sanitize_name(raw_op_id)

    return cst.FunctionDef(
        name=cst.Name(operation_id),
        params=cst.Parameters(params=params_list),
        body=req_body,
    )


def emit_functions(spec: OpenAPI) -> list[cst.FunctionDef]:
    """Emit a list of HTTP client methods for all paths in an OpenAPI spec.

    Args:
        spec: The parsed OpenAPI specification.

    Returns:
        A list of generated LibCST FunctionDef nodes for the methods.
    """
    methods: list[cst.FunctionDef] = []

    init_params = cst.Parameters(
        params=[
            cst.Param(name=cst.Name("self")),
            cst.Param(name=cst.Name("base_url"), annotation=cst.Annotation(cst.Name("str"))),
            cst.Param(
                name=cst.Name("api_key"),
                annotation=cst.Annotation(cst.Name("str")),
                default=cst.SimpleString('""'),
            ),
        ]
    )
    init_body = cst.IndentedBlock(
        body=[
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Attribute(value=cst.Name("self"), attr=cst.Name("base_url")))],
                        value=cst.Name("base_url"),
                    )
                ]
            ),
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Attribute(value=cst.Name("self"), attr=cst.Name("api_key")))],
                        value=cst.Name("api_key"),
                    )
                ]
            ),
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Attribute(value=cst.Name("self"), attr=cst.Name("http")))],
                        value=cst.Call(func=cst.Name("PoolManager")),
                    )
                ]
            ),
        ]
    )
    methods.append(cst.FunctionDef(name=cst.Name("__init__"), params=init_params, body=init_body))
    methods.append(
        cst.FunctionDef(
            name=cst.Name("close"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            returns=cst.Annotation(annotation=cst.Name("None")),
            body=cst.IndentedBlock(body=[cst.parse_statement("self.http.clear()")]),
        )
    )
    methods.append(
        cst.FunctionDef(
            name=cst.Name("__enter__"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            returns=cst.Annotation(annotation=cst.Name("Client")),
            body=cst.IndentedBlock(body=[cst.parse_statement("return self")]),
        )
    )
    methods.append(
        cst.FunctionDef(
            name=cst.Name("__exit__"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))],
                star_arg=cst.Param(
                    name=cst.Name("args"),
                    annotation=cst.Annotation(annotation=cst.Name("Any")),
                ),
            ),
            returns=cst.Annotation(annotation=cst.Name("None")),
            body=cst.IndentedBlock(body=[cst.parse_statement("self.close()")]),
        )
    )

    if spec.paths:
        for path, path_item in spec.paths.items():
            if path.startswith("/"):
                for method in HTTP_METHODS:
                    operation = getattr(path_item, method, None)
                    if operation:
                        methods.append(emit_function(method, path, operation))
                if getattr(path_item, "additionalOperations", None):
                    for custom_method, custom_op in (path_item.additionalOperations or {}).items():
                        methods.append(emit_function(custom_method.lower(), path, custom_op))

    return methods
