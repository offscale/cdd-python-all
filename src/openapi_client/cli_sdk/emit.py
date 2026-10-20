"""Module for generating a CLI script from an OpenAPI specification."""

from __future__ import annotations

from typing import Any

import libcst as cst

from openapi_client.functions.utils import (
    build_cst_module,
    get_default_server_url,
    map_openapi_type_to_python,
    sanitize_name,
)
from openapi_client.models import OpenAPI
from openapi_client.openapi.keywords import HTTP_METHODS


def extract_cli_operations(
    spec: OpenAPI,
) -> list[tuple[str, str, list[dict[str, Any]], dict[str, Any] | None]]:
    """Extract normalized CLI operation metadata from an OpenAPI specification.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        List of `(op_id, description, parameters_meta, request_body_meta)` tuples.
    """
    operations: list[tuple[str, str, list[dict[str, Any]], dict[str, Any] | None]] = []
    if not spec.paths:
        return operations

    for path, path_item in spec.paths.items():
        for method in HTTP_METHODS:
            operation = getattr(path_item, method, None)
            if not operation:
                continue
            raw_op_id = (
                operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
            )
            op_id = sanitize_name(raw_op_id)
            desc = operation.summary or f"{method.upper()} {path}"

            params_meta: list[dict[str, Any]] = []
            if operation.parameters:
                for param in operation.parameters:
                    p_name = getattr(param, "name", "param").replace("-", "_")
                    p_desc = getattr(param, "description", "") or ""
                    req = bool(getattr(param, "required", False))
                    p_type_raw: Any = "string"
                    if getattr(param, "schema_", None):
                        p_type_raw = (
                            getattr(param.schema_, "type", "string") or "string"
                        )
                        if isinstance(p_type_raw, list):
                            non_null = [t for t in p_type_raw if t != "null"]
                            p_type_raw = non_null[0] if non_null else p_type_raw[0]
                    py_type = map_openapi_type_to_python(str(p_type_raw))
                    params_meta.append(
                        {
                            "name": p_name,
                            "description": p_desc,
                            "required": req,
                            "py_type": py_type,
                        }
                    )

            body_meta: dict[str, Any] | None = None
            req_body = getattr(operation, "requestBody", None)
            if req_body is not None:
                body_desc = (
                    getattr(req_body, "description", None)
                    or "Request body JSON payload"
                )
                body_req = bool(getattr(req_body, "required", False))
                body_meta = {
                    "description": body_desc,
                    "required": body_req,
                }

            operations.append((op_id, desc, params_meta, body_meta))
    return operations


def emit_cli(spec: OpenAPI) -> cst.Module:
    """Generate a libcst.Module for a Python CLI application.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated LibCST Module node for the CLI script.
    """
    body: list[cst.BaseStatement | cst.EmptyLine] = []

    for mod_name in ("argparse", "json", "os", "sys"):
        body.append(
            cst.SimpleStatementLine(
                [cst.Import(names=[cst.ImportAlias(name=cst.Name(mod_name))])]
            )
        )
    body.append(
        cst.SimpleStatementLine(
            [
                cst.ImportFrom(
                    module=cst.Name("client"),
                    names=[cst.ImportAlias(name=cst.Name("Client"))],
                )
            ]
        )
    )
    body.append(cst.EmptyLine())

    main_body: list[cst.BaseStatement] = []

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("parser"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("argparse"), attr=cst.Name("ArgumentParser")
                        ),
                        args=[
                            cst.Arg(
                                value=cst.SimpleString('"Generated Client SDK CLI"'),
                                keyword=cst.Name("description"),
                            )
                        ],
                    ),
                )
            ]
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("subparsers"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("parser"), attr=cst.Name("add_subparsers")
                        ),
                        args=[
                            cst.Arg(
                                value=cst.SimpleString('"command"'),
                                keyword=cst.Name("dest"),
                            )
                        ],
                    ),
                )
            ]
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("mcp_parser"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("subparsers"), attr=cst.Name("add_parser")
                        ),
                        args=[
                            cst.Arg(value=cst.SimpleString('"mcp"')),
                            cst.Arg(
                                value=cst.SimpleString(
                                    '"Start the Model Context Protocol (MCP) server"'
                                ),
                                keyword=cst.Name("help"),
                            ),
                        ],
                    ),
                )
            ]
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("mcp_sse_parser"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("subparsers"), attr=cst.Name("add_parser")
                        ),
                        args=[
                            cst.Arg(value=cst.SimpleString('"mcp_sse"')),
                            cst.Arg(
                                value=cst.SimpleString(
                                    '"Start the Model Context Protocol (MCP) SSE server"'
                                ),
                                keyword=cst.Name("help"),
                            ),
                        ],
                    ),
                )
            ]
        )
    )

    for op_id, desc, params_meta, body_meta in extract_cli_operations(spec):
        main_body.append(
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(target=cst.Name(f"{op_id}_parser"))],
                        value=cst.Call(
                            func=cst.Attribute(
                                value=cst.Name("subparsers"),
                                attr=cst.Name("add_parser"),
                            ),
                            args=[
                                cst.Arg(value=cst.SimpleString(repr(op_id))),
                                cst.Arg(
                                    value=cst.SimpleString(repr(desc)),
                                    keyword=cst.Name("help"),
                                ),
                            ],
                        ),
                    )
                ]
            )
        )

        for p_info in params_meta:
            p_name = p_info["name"]
            p_desc = p_info["description"]
            req = p_info["required"]
            py_type = p_info["py_type"]
            type_expr: cst.BaseExpression = (
                cst.Attribute(value=cst.Name("json"), attr=cst.Name("loads"))
                if py_type in ("list", "dict")
                else cst.Name(py_type if py_type in ("int", "float", "str") else "str")
            )

            args_list = [
                cst.Arg(value=cst.SimpleString(f'"--{p_name}"')),
                cst.Arg(value=type_expr, keyword=cst.Name("type")),
                cst.Arg(
                    value=cst.SimpleString(repr(p_desc)),
                    keyword=cst.Name("help"),
                ),
            ]
            if req:
                args_list.append(
                    cst.Arg(
                        value=cst.Name("True"),
                        keyword=cst.Name("required"),
                    )
                )

            main_body.append(
                cst.SimpleStatementLine(
                    [
                        cst.Expr(
                            value=cst.Call(
                                func=cst.Attribute(
                                    value=cst.Name(f"{op_id}_parser"),
                                    attr=cst.Name("add_argument"),
                                ),
                                args=args_list,
                            )
                        )
                    ]
                )
            )

        if body_meta is not None:
            body_args_list = [
                cst.Arg(value=cst.SimpleString('"--body"')),
                cst.Arg(
                    value=cst.Attribute(value=cst.Name("json"), attr=cst.Name("loads")),
                    keyword=cst.Name("type"),
                ),
                cst.Arg(
                    value=cst.SimpleString(repr(body_meta["description"])),
                    keyword=cst.Name("help"),
                ),
            ]
            if body_meta["required"]:
                body_args_list.append(
                    cst.Arg(
                        value=cst.Name("True"),
                        keyword=cst.Name("required"),
                    )
                )
            main_body.append(
                cst.SimpleStatementLine(
                    [
                        cst.Expr(
                            value=cst.Call(
                                func=cst.Attribute(
                                    value=cst.Name(f"{op_id}_parser"),
                                    attr=cst.Name("add_argument"),
                                ),
                                args=body_args_list,
                            )
                        )
                    ]
                )
            )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("args"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("parser"), attr=cst.Name("parse_args")
                        )
                    ),
                )
            ]
        )
    )

    default_url = get_default_server_url(spec, fallback="http://localhost:8080/v2")
    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("c"))],
                    value=cst.Call(
                        func=cst.Name("Client"),
                        args=[
                            cst.Arg(
                                keyword=cst.Name("base_url"),
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("os"),
                                            attr=cst.Name("environ"),
                                        ),
                                        attr=cst.Name("get"),
                                    ),
                                    args=[
                                        cst.Arg(
                                            value=cst.SimpleString('"API_BASE_URL"')
                                        ),
                                        cst.Arg(
                                            value=cst.SimpleString(f'"{default_url}"')
                                        ),
                                    ],
                                ),
                            )
                        ],
                    ),
                )
            ]
        )
    )

    main_body.append(
        cst.If(
            test=cst.UnaryOperation(
                operator=cst.Not(),
                expression=cst.Attribute(
                    value=cst.Name("args"), attr=cst.Name("command")
                ),
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        [
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Name("parser"),
                                        attr=cst.Name("print_help"),
                                    )
                                )
                            )
                        ]
                    ),
                    cst.SimpleStatementLine(
                        [
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Name("sys"), attr=cst.Name("exit")
                                    ),
                                    args=[cst.Arg(value=cst.Integer("0"))],
                                )
                            )
                        ]
                    ),
                ]
            ),
        )
    )

    main_body.append(
        cst.If(
            test=cst.Comparison(
                left=cst.Attribute(value=cst.Name("args"), attr=cst.Name("command")),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(), comparator=cst.SimpleString('"mcp"')
                    )
                ],
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        [
                            cst.ImportFrom(
                                module=cst.Name("mcp_server"),
                                names=[
                                    cst.ImportAlias(name=cst.Name("start_mcp_server"))
                                ],
                            )
                        ]
                    ),
                    cst.SimpleStatementLine(
                        [
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Name("start_mcp_server"),
                                    args=[cst.Arg(value=cst.Name("c"))],
                                )
                            )
                        ]
                    ),
                    cst.SimpleStatementLine(
                        [
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Name("sys"), attr=cst.Name("exit")
                                    ),
                                    args=[cst.Arg(value=cst.Integer("0"))],
                                )
                            )
                        ]
                    ),
                ]
            ),
        )
    )

    main_body.append(
        cst.If(
            test=cst.Comparison(
                left=cst.Attribute(value=cst.Name("args"), attr=cst.Name("command")),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(), comparator=cst.SimpleString('"mcp_sse"')
                    )
                ],
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        [
                            cst.ImportFrom(
                                module=cst.Name("mcp_sse_server"),
                                names=[
                                    cst.ImportAlias(
                                        name=cst.Name("start_mcp_sse_server")
                                    )
                                ],
                            )
                        ]
                    ),
                    cst.SimpleStatementLine(
                        [
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Name("start_mcp_sse_server"),
                                    args=[cst.Arg(value=cst.Name("c"))],
                                )
                            )
                        ]
                    ),
                    cst.SimpleStatementLine(
                        [
                            cst.Expr(
                                value=cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Name("sys"), attr=cst.Name("exit")
                                    ),
                                    args=[cst.Arg(value=cst.Integer("0"))],
                                )
                            )
                        ]
                    ),
                ]
            ),
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("method"))],
                    value=cst.Call(
                        func=cst.Name("getattr"),
                        args=[
                            cst.Arg(value=cst.Name("c")),
                            cst.Arg(
                                value=cst.Attribute(
                                    value=cst.Name("args"), attr=cst.Name("command")
                                )
                            ),
                        ],
                    ),
                )
            ]
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("kwargs"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Call(
                                func=cst.Name("vars"),
                                args=[cst.Arg(value=cst.Name("args"))],
                            ),
                            attr=cst.Name("copy"),
                        )
                    ),
                )
            ]
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("kwargs"), attr=cst.Name("pop")
                        ),
                        args=[cst.Arg(value=cst.SimpleString('"command"'))],
                    )
                )
            ]
        )
    )

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Expr(
                    value=cst.Call(
                        func=cst.Name("print"),
                        args=[
                            cst.Arg(
                                value=cst.Call(
                                    func=cst.Name("method"),
                                    args=[
                                        cst.Arg(
                                            value=cst.Name("kwargs"),
                                            star="**",
                                            keyword=None,
                                        )
                                    ],
                                )
                            )
                        ],
                    )
                )
            ]
        )
    )

    main_func = cst.FunctionDef(
        name=cst.Name("main"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=main_body),
    )
    body.append(main_func)

    body.append(
        cst.If(
            test=cst.Comparison(
                left=cst.Name("__name__"),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(), comparator=cst.SimpleString('"__main__"')
                    )
                ],
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        [cst.Expr(value=cst.Call(func=cst.Name("main")))]
                    )
                ]
            ),
        )
    )

    return build_cst_module(body)


def emit_cli_sdk(spec: OpenAPI) -> str:
    """Generate the Python source code string for a CLI application.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated Python CLI code string.
    """
    return emit_cli(spec).code
