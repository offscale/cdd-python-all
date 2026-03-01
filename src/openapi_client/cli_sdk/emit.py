"""Module for generating a CLI script from an OpenAPI specification."""

import libcst as cst
from openapi_client.models import OpenAPI


def emit_cli(spec: OpenAPI) -> cst.Module:
    """Generate a libcst.Module for a Python CLI application."""

    body = []

    # Imports
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

    main_body = []

    # parser = argparse.ArgumentParser(...)
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
                                value=cst.SimpleString(
                                    f'"{spec.info.title if spec.info else "API"} CLI"'
                                ),
                                keyword=cst.Name("description"),
                            )
                        ],
                    ),
                )
            ]
        )
    )

    # subparsers = parser.add_subparsers(dest="command")
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

    if spec.paths:
        for path, path_item in spec.paths.items():
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    desc = operation.summary or f"{method.upper()} {path}"

                    # op_parser = subparsers.add_parser("op_id", help="desc")
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

                            # op_parser.add_argument(...)
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

    # args = parser.parse_args()
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

    # c = Client()
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

    # if not args.command: parser.print_help(); sys.exit(0)
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

    # method = getattr(c, args.command)
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

    # kwargs = vars(args).copy()
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

    # kwargs.pop("command")
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

    # print(method(**kwargs))
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
                        ],  # type: ignore
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

    return cst.Module(body=body)  # type: ignore


def emit_cli_sdk(spec: OpenAPI) -> str:
    """Generate the Python source code string for a CLI application."""
    return emit_cli(spec).code
