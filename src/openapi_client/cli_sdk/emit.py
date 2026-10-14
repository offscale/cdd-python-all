"""Module for generating a CLI script from an OpenAPI specification."""

from __future__ import annotations

import libcst as cst

from openapi_client.functions.utils import sanitize_name
from openapi_client.models import OpenAPI


def emit_cli(spec: OpenAPI) -> cst.Module:
    """Generate a libcst.Module for a Python CLI application.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated LibCST Module node for the CLI script.
    """
    body: list[cst.BaseStatement | cst.EmptyLine] = []

    body.append(
        cst.SimpleStatementLine(
            [cst.Import(names=[cst.ImportAlias(name=cst.Name("argparse"))])]
        )
    )
    body.append(
        cst.SimpleStatementLine(
            [cst.Import(names=[cst.ImportAlias(name=cst.Name("sys"))])]
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

    if spec.paths:
        for path, path_item in spec.paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    raw_op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    op_id = sanitize_name(raw_op_id)
                    desc = operation.summary or f"{method.upper()} {path}"

                    main_body.append(
                        cst.SimpleStatementLine(
                            [
                                cst.Assign(
                                    targets=[
                                        cst.AssignTarget(
                                            target=cst.Name(f"{op_id}_parser")
                                        )
                                    ],
                                    value=cst.Call(
                                        func=cst.Attribute(
                                            value=cst.Name("subparsers"),
                                            attr=cst.Name("add_parser"),
                                        ),
                                        args=[
                                            cst.Arg(
                                                value=cst.SimpleString(f'"{op_id}"')
                                            ),
                                            cst.Arg(
                                                value=cst.SimpleString(f'"{desc}"'),
                                                keyword=cst.Name("help"),
                                            ),
                                        ],
                                    ),
                                )
                            ]
                        )
                    )

                    if operation.parameters:
                        for param in operation.parameters:
                            p_name = getattr(param, "name", "param").replace("-", "_")
                            p_desc = getattr(param, "description", "")
                            req = getattr(param, "required", False)

                            args_list = [
                                cst.Arg(value=cst.SimpleString(f'"--{p_name}"')),
                                cst.Arg(
                                    value=cst.Name("str"), keyword=cst.Name("type")
                                ),
                                cst.Arg(
                                    value=cst.SimpleString(f'"{p_desc}"'),
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

    main_body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("c"))],
                    value=cst.Call(func=cst.Name("Client")),
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

    return cst.Module(body=body)


def emit_cli_sdk(spec: OpenAPI) -> str:
    """Generate the Python source code string for a CLI application.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated Python CLI code string.
    """
    return emit_cli(spec).code
