"""Emit FastAPI server code using LibCST AST construction."""

from __future__ import annotations

import re

import libcst as cst

from openapi_client.dao.emit import _doc_stmt
from openapi_client.functions.emit import _safe_param_name
from openapi_client.functions.utils import (
    build_cst_module,
    get_annotation_for_schema,
    sanitize_class_name,
    sanitize_name,
)
from openapi_client.models import OpenAPI, Operation
from openapi_client.openapi.keywords import HTTP_METHODS


def _match_model_for_tag(tag: str, spec: OpenAPI) -> str | None:
    """Find a component schema with properties matching a route tag.

    Args:
        tag: Sanitized route tag (e.g. `'users'` or `'pet'`).
        spec: The OpenAPI specification model.

    Returns:
        The raw schema key in `spec.components.schemas` if matched, else `None`.
    """
    if not spec.components or not spec.components.schemas:
        return None
    singular = tag[:-1] if tag.endswith("s") and len(tag) > 1 else tag
    for name, schema in spec.components.schemas.items():
        if not (hasattr(schema, "properties") and schema.properties):
            continue
        s_name = sanitize_name(name)
        if s_name in (tag, singular) or f"{s_name}s" == tag:
            return name
    return None


def _extract_request_body_type(operation: Operation) -> str:
    """Resolve the type annotation string for an operation's requestBody.

    Args:
        operation: The OpenAPI Operation object.

    Returns:
        A Python type annotation string for the `body` parameter.
    """
    rb = operation.requestBody
    content = getattr(rb, "content", None) if rb else None
    if isinstance(content, dict) and content:
        media = content.get("application/json") or next(iter(content.values()))
        schema_obj = getattr(media, "schema_", getattr(media, "schema", None))
        ann = get_annotation_for_schema(schema_obj)
        if ann and ann != "Any":
            if not ann.startswith(("dict", "list", "str", "int", "float", "bool")):
                return f"models.{ann} | dict[str, Any] | None"
            return f"{ann} | None"
    return "dict[str, Any] | None"


def _extract_response_type(operation: Operation) -> str | None:
    """Resolve the return type annotation string from an operation's responses.

    Args:
        operation: The OpenAPI Operation object.

    Returns:
        A Python return type annotation string if a typed response schema exists, else `None`.
    """
    responses = getattr(operation, "responses", None)
    if not isinstance(responses, dict):
        return None
    for code in ("200", "201", "default"):
        resp = responses.get(code)
        content = getattr(resp, "content", None) if resp else None
        if isinstance(content, dict) and content:
            media = content.get("application/json") or next(iter(content.values()))
            schema_obj = getattr(media, "schema_", getattr(media, "schema", None))
            if schema_obj is not None:
                ann = get_annotation_for_schema(schema_obj)
                if ann and ann != "Any":
                    if not ann.startswith(
                        ("dict", "list", "str", "int", "float", "bool")
                    ):
                        return f"models.{ann} | dict[str, Any] | None"
                    return f"{ann} | dict[str, Any] | None"
    return None


def _build_route_function(
    method: str,
    path: str,
    operation: Operation,
    matched_model: str | None,
) -> cst.FunctionDef:
    """Build a LibCST FunctionDef node for a single FastAPI route handler.

    Args:
        method: HTTP verb (`'get'`, `'post'`, `'put'`, `'delete'`, `'patch'`).
        path: Route path string.
        operation: The OpenAPI Operation object.
        matched_model: Optional matching model name in `spec.components.schemas`.

    Returns:
        A LibCST FunctionDef node with `@router.<method>(path)` decorator.
    """
    raw_op_id = operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
    op_id = sanitize_name(raw_op_id)
    nl = chr(10)
    doc_text = f"{operation.summary or ''}{nl}    {operation.description or ''}"

    params: list[cst.Param] = []
    seen_params: set[str] = set()

    path_vars = re.findall(r"\{([^}]+)\}", path)
    if operation.parameters:
        for param in operation.parameters:
            safe_p = _safe_param_name(getattr(param, "name", "") or "")
            if safe_p and safe_p not in seen_params:
                seen_params.add(safe_p)
                schema_obj = getattr(param, "schema_", getattr(param, "schema", None))
                ann_str = get_annotation_for_schema(schema_obj)
                params.append(
                    cst.Param(
                        name=cst.Name(safe_p),
                        annotation=cst.Annotation(
                            cst.parse_expression(f"{ann_str} | Any")
                        ),
                        default=cst.Name("None"),
                    )
                )

    for p_var in path_vars:
        safe_var = _safe_param_name(p_var)
        if safe_var not in seen_params:
            seen_params.add(safe_var)
            params.append(
                cst.Param(
                    name=cst.Name(safe_var),
                    annotation=cst.Annotation(cst.Name("Any")),
                    default=cst.Name("None"),
                )
            )

    has_body = operation.requestBody is not None or (
        matched_model is not None and method in ("post", "put", "patch")
    )
    if operation.requestBody is not None and "body" not in seen_params:
        seen_params.add("body")
        body_type = _extract_request_body_type(operation)
        params.append(
            cst.Param(
                name=cst.Name("body"),
                annotation=cst.Annotation(cst.parse_expression(body_type)),
                default=cst.Name("None"),
            )
        )

    body_stmts: list[cst.BaseStatement] = [_doc_stmt(doc_text)]

    if matched_model is not None:
        class_name = sanitize_class_name(matched_model)
        pk_var = _safe_param_name(path_vars[0]) if path_vars else None
        dao_call = f"dao = get_dao({matched_model!r}, session=db, ephemeral=bool(os.environ.get('EPHEMERAL_DB')))"
        inner_stmts: list[cst.BaseStatement] = [cst.parse_statement(dao_call)]

        if method == "get" and pk_var:
            inner_stmts.append(cst.parse_statement(f"item = dao.get_by_id({pk_var})"))
            inner_stmts.append(
                cst.parse_statement(
                    "return {k: v for k, v in item.__dict__.items() if not k.startswith('_')} if item is not None else None"
                )
            )
        elif method == "get":
            inner_stmts.append(
                cst.parse_statement(
                    "return [{k: v for k, v in item.__dict__.items() if not k.startswith('_')} for item in dao.get_all()]"
                )
            )
        elif method == "delete" and pk_var:
            inner_stmts.append(
                cst.parse_statement(f"return {{'deleted': dao.delete({pk_var})}}")
            )
        elif method in ("post", "put", "patch") and "body" in seen_params:
            inner_stmts.append(
                cst.parse_statement(
                    "payload = body if isinstance(body, dict) else (body.model_dump() if hasattr(body, 'model_dump') else {})"
                )
            )
            inner_stmts.append(cst.parse_statement(f"obj = models.{class_name}()"))
            inner_stmts.append(
                cst.For(
                    target=cst.Tuple(
                        elements=[
                            cst.Element(cst.Name("k")),
                            cst.Element(cst.Name("v")),
                        ],
                        lpar=[],
                        rpar=[],
                    ),
                    iter=cst.parse_expression("payload.items()"),
                    body=cst.IndentedBlock(
                        body=[cst.parse_statement("setattr(obj, k, v)")]
                    ),
                )
            )
            inner_stmts.append(cst.parse_statement("created = dao.create(obj)"))
            inner_stmts.append(
                cst.parse_statement(
                    "return {k: v for k, v in created.__dict__.items() if not k.startswith('_')}"
                )
            )
        else:
            inner_stmts.append(cst.parse_statement("dao.get_all()"))
            inner_stmts.append(
                cst.parse_statement('return {"message": "Not implemented"}')
            )

        _ = has_body
        try_stmt = cst.Try(
            body=cst.IndentedBlock(
                body=[
                    cst.parse_statement("gen = get_db_session()"),
                    cst.parse_statement("db = next(gen)"),
                    cst.Try(
                        body=cst.IndentedBlock(body=inner_stmts),
                        finalbody=cst.Finally(
                            body=cst.IndentedBlock(
                                body=[cst.parse_statement("gen.close()")]
                            )
                        ),
                    ),
                ]
            ),
            handlers=[
                cst.ExceptHandler(
                    type=cst.parse_expression(
                        "(RuntimeError, NotImplementedError, ValueError)"
                    ),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement('return {"message": "Not implemented"}')
                        ]
                    ),
                )
            ],
        )
        body_stmts.append(try_stmt)
    else:
        body_stmts.append(cst.parse_statement('return {"message": "Not implemented"}'))

    decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Attribute(value=cst.Name("router"), attr=cst.Name(method)),
            args=[cst.Arg(value=cst.SimpleString(repr(path)))],
        )
    )

    resp_type = _extract_response_type(operation)
    returns_ann = (
        cst.Annotation(annotation=cst.parse_expression(resp_type))
        if resp_type is not None
        else None
    )

    return cst.FunctionDef(
        name=cst.Name(op_id),
        params=cst.Parameters(params=params),
        returns=returns_ann,
        decorators=[decorator],
        body=cst.IndentedBlock(body=body_stmts),
    )


def _build_main_module(spec: OpenAPI, router_tags: list[str]) -> cst.Module:
    """Build the LibCST Module for `main.py`.

    Args:
        spec: The OpenAPI specification model.
        router_tags: List of sanitized router tag names to include.

    Returns:
        A LibCST Module representing `main.py`.
    """
    body: list[cst.BaseStatement | cst.EmptyLine] = [
        cst.parse_statement("from __future__ import annotations"),
        cst.parse_statement("import argparse"),
        cst.parse_statement("import os"),
        cst.parse_statement("import uvicorn"),
        cst.parse_statement("from fastapi import FastAPI, HTTPException, Request"),
        cst.parse_statement("from fastapi.middleware.cors import CORSMiddleware"),
        cst.parse_statement("from pydantic import BaseModel"),
        cst.parse_statement("from typing import Any"),
        cst.parse_statement("import models"),
        cst.parse_statement("from db import setup_database, get_db_session"),
        cst.parse_statement("from seeder import seed_database"),
        cst.EmptyLine(),
    ]

    app_args = [
        cst.Arg(
            keyword=cst.Name("title"), value=cst.SimpleString(repr(spec.info.title))
        ),
        cst.Arg(
            keyword=cst.Name("version"),
            value=cst.SimpleString(repr(spec.info.version)),
        ),
    ]
    if spec.info.description:
        app_args.append(
            cst.Arg(
                keyword=cst.Name("description"),
                value=cst.SimpleString(repr(spec.info.description)),
            )
        )

    body.append(
        cst.SimpleStatementLine(
            [
                cst.Assign(
                    targets=[cst.AssignTarget(cst.Name("app"))],
                    value=cst.Call(func=cst.Name("FastAPI"), args=app_args),
                )
            ]
        )
    )
    body.append(cst.EmptyLine())
    body.append(
        cst.parse_statement(
            "app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])"
        )
    )
    body.append(
        cst.parse_statement(
            "config_flags = {'strict_validation': False, 'enforce_auth': False}"
        )
    )
    body.append(cst.EmptyLine())

    middleware_fn = cst.FunctionDef(
        name=cst.Name("mock_server_middleware"),
        asynchronous=cst.Asynchronous(),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("request"),
                    annotation=cst.Annotation(cst.Name("Request")),
                ),
                cst.Param(name=cst.Name("call_next")),
            ]
        ),
        decorators=[
            cst.Decorator(decorator=cst.parse_expression("app.middleware('http')"))
        ],
        body=cst.IndentedBlock(
            body=[
                _doc_stmt("Advanced mock capabilities middleware."),
                cst.If(
                    test=cst.parse_expression("config_flags['strict_validation']"),
                    body=cst.IndentedBlock(
                        body=[
                            cst.If(
                                test=cst.parse_expression(
                                    "request.method in ('POST', 'PUT', 'PATCH') and not request.headers.get('content-type')"
                                ),
                                body=cst.IndentedBlock(
                                    body=[
                                        cst.parse_statement(
                                            "from fastapi.responses import JSONResponse"
                                        ),
                                        cst.parse_statement(
                                            "return JSONResponse(status_code=422, content={'message': 'Missing Content-Type header'})"
                                        ),
                                    ]
                                ),
                            )
                        ]
                    ),
                ),
                cst.If(
                    test=cst.parse_expression(
                        "config_flags['enforce_auth'] and request.url.path != '/_mock/trigger-webhook'"
                    ),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement(
                                "auth_header = request.headers.get('Authorization')"
                            ),
                            cst.If(
                                test=cst.parse_expression(
                                    "not auth_header or not auth_header.startswith('Bearer mock-token')"
                                ),
                                body=cst.IndentedBlock(
                                    body=[
                                        cst.parse_statement(
                                            "from fastapi.responses import JSONResponse"
                                        ),
                                        cst.parse_statement(
                                            "return JSONResponse(status_code=401, content={'message': 'Unauthorized'})"
                                        ),
                                    ]
                                ),
                            ),
                        ]
                    ),
                ),
                cst.parse_statement("return await call_next(request)"),
            ]
        ),
    )
    body.append(middleware_fn)
    body.append(cst.EmptyLine())

    webhook_fn = cst.FunctionDef(
        name=cst.Name("trigger_webhook"),
        asynchronous=cst.Asynchronous(),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("webhook_name"),
                    annotation=cst.Annotation(cst.Name("str")),
                )
            ]
        ),
        decorators=[
            cst.Decorator(
                decorator=cst.parse_expression(
                    "app.post('/_mock/trigger-webhook/{webhook_name}')"
                )
            )
        ],
        body=cst.IndentedBlock(
            body=[
                _doc_stmt("Administrative trigger for outgoing webhooks."),
                cst.parse_statement(
                    "return {'status': 'webhook triggered', 'webhook_name': webhook_name}"
                ),
            ]
        ),
    )
    body.append(webhook_fn)

    auth_endpoints = [
        (
            "auth_register",
            "/auth/register",
            "Integrated Identity Provider: Register.",
            "{'token': 'mock-token-registered'}",
        ),
        (
            "auth_login",
            "/auth/login",
            "Integrated Identity Provider: Login.",
            "{'token': 'mock-token-123'}",
        ),
        (
            "auth_refresh",
            "/auth/refresh",
            "Integrated Identity Provider: Refresh.",
            "{'token': 'mock-token-refreshed'}",
        ),
        (
            "auth_logout",
            "/auth/logout",
            "Integrated Identity Provider: Logout.",
            "{'status': 'logged out'}",
        ),
    ]
    for fn_name, route_path, doc_str, ret_expr in auth_endpoints:
        body.append(
            cst.FunctionDef(
                name=cst.Name(fn_name),
                asynchronous=cst.Asynchronous(),
                params=cst.Parameters(),
                decorators=[
                    cst.Decorator(
                        decorator=cst.parse_expression(f"app.post({route_path!r})")
                    )
                ],
                body=cst.IndentedBlock(
                    body=[_doc_stmt(doc_str), cst.parse_statement(f"return {ret_expr}")]
                ),
            )
        )

    for tag in router_tags:
        body.append(
            cst.parse_statement(f"from routes.{tag} import router as {tag}_router")
        )
        body.append(cst.parse_statement(f"app.include_router({tag}_router)"))

    main_fn = cst.FunctionDef(
        name=cst.Name("main"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    """Main server entrypoint.
    Parses CLI arguments, sets up DAOs and Database, and starts the server."""
                ),
                cst.parse_statement(
                    "parser = argparse.ArgumentParser(description='Run the CDD server.')"
                ),
                cst.parse_statement(
                    "parser.add_argument('--ephemeral', action='store_true', help='Triggers the Concrete DAOs and overrides DATABASE_URL with a throwaway database.')"
                ),
                cst.parse_statement(
                    "parser.add_argument('--seed', action='store_true', help='Runs the fake data seeder on startup (requires a concrete DB connection).')"
                ),
                cst.parse_statement(
                    "parser.add_argument('--strict-validation', action='store_true', help='Enable strict OpenAPI request validation.')"
                ),
                cst.parse_statement(
                    "parser.add_argument('--enforce-auth', action='store_true', help='Enforce authentication (mock tokens in ephemeral mode).')"
                ),
                cst.parse_statement(
                    "parser.add_argument('--start-auth-server', action='store_true', help='Run the identity provider endpoints.')"
                ),
                cst.parse_statement("args, unknown = parser.parse_known_args()"),
                cst.parse_statement(
                    "config_flags['strict_validation'] = args.strict_validation"
                ),
                cst.parse_statement("config_flags['enforce_auth'] = args.enforce_auth"),
                cst.parse_statement(
                    "config_flags['start_auth_server'] = args.start_auth_server"
                ),
                cst.If(
                    test=cst.parse_expression("args.ephemeral"),
                    body=cst.IndentedBlock(
                        body=[cst.parse_statement("os.environ['EPHEMERAL_DB'] = '1'")]
                    ),
                ),
                cst.parse_statement("setup_database(ephemeral=args.ephemeral)"),
                cst.parse_statement(
                    "has_db = bool(os.environ.get('DATABASE_URL')) or args.ephemeral"
                ),
                cst.If(
                    test=cst.parse_expression("args.seed and has_db"),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement("db_gen = get_db_session()"),
                            cst.parse_statement("db = next(db_gen)"),
                            cst.Try(
                                body=cst.IndentedBlock(
                                    body=[cst.parse_statement("seed_database(db)")]
                                ),
                                finalbody=cst.Finally(
                                    body=cst.IndentedBlock(
                                        body=[cst.parse_statement("db_gen.close()")]
                                    )
                                ),
                            ),
                        ]
                    ),
                ),
                cst.parse_statement("port = int(os.environ.get('PORT', 8000))"),
                cst.parse_statement("uvicorn.run(app, host='0.0.0.0', port=port)"),
            ]
        ),
    )
    body.append(cst.EmptyLine())
    body.append(main_fn)
    body.append(
        cst.If(
            test=cst.parse_expression("__name__ == '__main__'"),
            body=cst.IndentedBlock(body=[cst.parse_statement("main()")]),
        )
    )

    return build_cst_module(body)


def emit_fastapi(spec: OpenAPI) -> dict[str, str]:
    """Generate a FastAPI server from OpenAPI in a modular way using LibCST AST.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        A dictionary mapping relative file paths to generated Python code strings.
    """
    files: dict[str, str] = {}
    router_modules: dict[str, list[cst.BaseStatement | cst.EmptyLine]] = {}
    router_has_dao: dict[str, bool] = {}

    if spec.paths:
        for path, path_item in spec.paths.items():
            raw_tag = "default"
            parts = path.split("/")
            if len(parts) > 1 and parts[1]:
                raw_tag = parts[1]
            tag = sanitize_name(raw_tag) or "default"
            matched_model = _match_model_for_tag(tag, spec)

            if tag not in router_modules:
                router_modules[tag] = [
                    cst.parse_statement("from __future__ import annotations"),
                    cst.parse_statement("import os"),
                    cst.parse_statement("from typing import Any"),
                    cst.parse_statement("from fastapi import APIRouter"),
                    cst.EmptyLine(),
                    cst.parse_statement(f"router = APIRouter(tags=[{raw_tag!r}])"),
                    cst.EmptyLine(),
                ]
                router_has_dao[tag] = False

            if matched_model is not None and not router_has_dao[tag]:
                router_modules[tag].insert(
                    4, cst.parse_statement("from dao import get_dao")
                )
                router_modules[tag].insert(
                    5, cst.parse_statement("from db import get_db_session")
                )
                router_modules[tag].insert(6, cst.parse_statement("import models"))
                router_has_dao[tag] = True

            for method in HTTP_METHODS:
                operation = getattr(path_item, method, None)
                if operation:
                    fn_node = _build_route_function(
                        method, path, operation, matched_model
                    )
                    router_modules[tag].append(fn_node)
                    router_modules[tag].append(cst.EmptyLine())

    for tag, stmts in router_modules.items():
        files[f"routes/{tag}.py"] = build_cst_module(stmts).code

    files["routes/__init__.py"] = ""
    files["main.py"] = _build_main_module(spec, list(router_modules.keys())).code

    return files
