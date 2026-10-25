"""Module for emitting pytest tests from OpenAPI examples."""

from __future__ import annotations

from typing import Any

import libcst as cst
from openapi_client.functions.utils import (
    build_cst_module,
    get_annotation_for_schema,
    get_test_base_url,
    safe_param_name,
    sanitize_name,
)
from openapi_client.models import OpenAPI, Operation
from openapi_client.openapi.keywords import HTTP_METHODS


def get_dummy_value_for_schema(schema_obj: Any) -> cst.BaseExpression:
    """Return a libcst BaseExpression for a dummy value based on schema type.

    Args:
        schema_obj: The OpenAPI Schema or Parameter object.

    Returns:
        A LibCST expression representing a valid dummy value for the schema.
    """
    if schema_obj is not None:
        example = getattr(schema_obj, "example", None)
        if example is None:
            example = getattr(schema_obj, "default", None)
        if example is None:
            enum_vals = getattr(schema_obj, "enum", None)
            if isinstance(enum_vals, list) and enum_vals:
                example = enum_vals[0]
        if isinstance(example, str):
            return cst.SimpleString(f'"{example}"')
        if isinstance(example, bool):
            return cst.Name("True" if example else "False")
        if isinstance(example, int):
            return cst.Integer(str(example))
        if isinstance(example, float):
            return cst.Float(str(example))

    ann = get_annotation_for_schema(schema_obj)
    if ann == "str":
        fmt = getattr(schema_obj, "format", None) if schema_obj else None
        if fmt in ("uri", "url"):
            return cst.SimpleString('"http://example.com"')
        return cst.SimpleString('"test_string"')
    elif ann == "int":
        return cst.Integer("1")
    elif ann == "float":
        return cst.Float("1.0")
    elif ann == "bool":
        return cst.Name("True")
    elif ann.startswith("list"):
        if "str" in ann:
            items = getattr(schema_obj, "items", None)
            item_val = get_dummy_value_for_schema(items)
            return cst.List(elements=[cst.Element(item_val)])
        elif "int" in ann:
            return cst.List(elements=[cst.Element(cst.Integer("1"))])
        else:
            return cst.List(elements=[])
    elif ann.startswith("dict"):
        return cst.Dict(elements=[])
    else:
        t = getattr(schema_obj, "type", None) if schema_obj else None
        if t == "file":
            return cst.SimpleString('b"dummy_content"')
        return cst.Name("None")


def get_stub_body(schema_obj: Any, spec: OpenAPI | None = None) -> cst.BaseExpression:
    """Generate a stub body AST node based on an OpenAPI schema object.

    Args:
        schema_obj: The OpenAPI Schema or Reference for the request body.
        spec: Optional full OpenAPI specification for `$ref` resolution.

    Returns:
        A LibCST Dict or List node representing a valid stub request body.
    """
    if schema_obj and getattr(schema_obj, "ref", None) and spec and spec.components and spec.components.schemas:
        ref_name = schema_obj.ref.split("/")[-1]
        schema_obj = spec.components.schemas.get(ref_name, schema_obj)

    if schema_obj and getattr(schema_obj, "properties", None):
        elements = []
        for prop_name, prop_schema in schema_obj.properties.items():
            if getattr(prop_schema, "ref", None) or (
                getattr(prop_schema, "type", None) in ("object", "array")
                and getattr(getattr(prop_schema, "items", None), "type", None)
                not in ("string", "integer", "number", "boolean")
            ):
                val = get_stub_body(prop_schema, spec)
            else:
                val = get_dummy_value_for_schema(prop_schema)
            elements.append(cst.DictElement(key=cst.SimpleString(f'"{prop_name}"'), value=val))
        return cst.Dict(elements=elements)
    elif schema_obj and getattr(schema_obj, "type", None) == "array":
        items_schema = getattr(schema_obj, "items", None)
        if items_schema and getattr(items_schema, "type", None) in (
            "string",
            "integer",
            "number",
            "boolean",
        ):
            item_val = get_dummy_value_for_schema(items_schema)
        else:
            item_val = get_stub_body(items_schema, spec)
        return cst.List(elements=[cst.Element(item_val)])
    else:
        return cst.Dict(elements=[])


def emit_operation_test(
    method: str,
    path: str,
    operation: Operation,
    composable: bool = False,
    spec: OpenAPI | None = None,
) -> cst.FunctionDef:
    """Emit a pytest unit test for an API operation.

    Args:
        method: HTTP verb (e.g., `'get'`, `'post'`).
        path: Route path string.
        operation: The OpenAPI Operation object.
        composable: If True, accepts a `client` pytest fixture and asserts status codes.
        spec: Optional full OpenAPI specification for `$ref` and server resolution.

    Returns:
        The generated LibCST FunctionDef node for the test.
    """
    raw_op_id = operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
    op_id = sanitize_name(raw_op_id)
    func_name = f"test_{op_id}"

    req_entries: list[tuple[str, cst.BaseExpression, bool]] = []
    opt_entries: list[tuple[str, cst.BaseExpression, bool]] = []
    has_body_param = False
    use_positional_body = False

    if operation.parameters:
        for param in operation.parameters:
            if hasattr(param, "name"):
                param_name = safe_param_name(param.name)
                p_in = getattr(param, "in_", getattr(param, "in", None))
                schema_obj = getattr(param, "schema_", getattr(param, "schema", None))
                if not schema_obj and getattr(param, "type", None):
                    schema_obj = param

                if p_in == "body":
                    has_body_param = True
                    val = get_stub_body(schema_obj, spec)
                    is_unnamed_body = param_name == "body" and composable
                    if is_unnamed_body:
                        use_positional_body = True
                else:
                    val = get_dummy_value_for_schema(schema_obj)
                    is_unnamed_body = False

                param_default = getattr(param, "default", None)
                if param_default is None and schema_obj is not None:
                    param_default = getattr(schema_obj, "default", None)
                if param_default is not None:
                    opt_entries.append((param_name, val, is_unnamed_body))
                else:
                    req_entries.append((param_name, val, is_unnamed_body))

    if operation.requestBody and not has_body_param:
        content = getattr(operation.requestBody, "content", None)
        if isinstance(content, dict) and content:
            schema_obj = None
            if "application/json" in content:
                media = content["application/json"]
                schema_obj = getattr(media, "schema_", getattr(media, "schema", None))
            elif "application/xml" in content:
                media = content["application/xml"]
                schema_obj = getattr(media, "schema_", getattr(media, "schema", None))
            else:
                first_media = next(iter(content.values()))
                schema_obj = getattr(first_media, "schema_", getattr(first_media, "schema", None))
            val = get_stub_body(schema_obj, spec)
        else:
            val = cst.Dict(elements=[])

        if composable:
            use_positional_body = True
        opt_entries.append(("body", val, composable))

    ordered_entries = req_entries + opt_entries
    args: list[cst.Arg] = []
    for p_name, p_val, is_pos_body in ordered_entries:
        if use_positional_body or is_pos_body:
            args.append(cst.Arg(value=p_val))
        else:
            args.append(cst.Arg(keyword=cst.Name(p_name), value=p_val))

    method_call = cst.Call(
        func=cst.Attribute(value=cst.Name("client"), attr=cst.Name(op_id)),
        args=args,
    )

    if composable:
        responses = getattr(operation, "responses", None) or {}
        has_only_200 = (
            "200" in responses
            and method.lower() == "get"
            and "{" not in path
            and not any(str(code).startswith("4") for code in responses)
        )

        status_expr = cst.Call(
            func=cst.Name("getattr"),
            args=[
                cst.Arg(cst.Name("response")),
                cst.Arg(cst.SimpleString('"status"')),
                cst.Arg(cst.Integer("200")),
            ],
        )
        if has_only_200:
            assertion_test = cst.Comparison(
                left=status_expr,
                comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.Integer("200"))],
            )
        else:
            assertion_test = cst.Comparison(
                left=status_expr,
                comparisons=[cst.ComparisonTarget(operator=cst.LessThan(), comparator=cst.Integer("500"))],
            )

        body: list[cst.BaseStatement] = [
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("response"))],
                        value=method_call,
                    )
                ]
            ),
            cst.SimpleStatementLine([cst.Assert(test=assertion_test)]),
            cst.SimpleStatementLine([cst.Import(names=[cst.ImportAlias(name=cst.Name("json"))])]),
            cst.parse_statement(
                """if getattr(response, "data", None):
    payload = response.json() if hasattr(response, "json") else json.loads(response.data.decode("utf-8"))
    assert payload is not None
    if isinstance(payload, dict):
        assert "sabotage" not in payload
elif isinstance(response, dict):
    assert "sabotage" not in response"""
            ),
        ]

        params = cst.Parameters(params=[cst.Param(name=cst.Name("client"))])
    else:
        default_url = get_test_base_url(spec, default_prefix="/api/v3")
        body = [
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("client"))],
                        value=cst.Call(
                            func=cst.Name("Client"),
                            args=[
                                cst.Arg(cst.SimpleString(f'"{default_url}"')),
                                cst.Arg(
                                    keyword=cst.Name("api_key"),
                                    value=cst.SimpleString('"special-key"'),
                                ),
                            ],
                        ),
                    )
                ]
            ),
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("response"))],
                        value=method_call,
                    )
                ]
            ),
            cst.SimpleStatementLine(
                [
                    cst.Assert(
                        test=cst.Comparison(
                            left=cst.Name("response"),
                            comparisons=[cst.ComparisonTarget(operator=cst.IsNot(), comparator=cst.Name("None"))],
                        )
                    )
                ]
            ),
        ]
        params = cst.Parameters()

    return cst.FunctionDef(
        name=cst.Name(func_name),
        params=params,
        body=cst.IndentedBlock(body=body),
    )


def emit_tests(spec: OpenAPI, composable: bool = False) -> cst.Module:
    """Emit a pytest test module for the OpenAPI spec.

    Args:
        spec: The OpenAPI specification model.
        composable: If True, emits a `client` pytest fixture and composable tests.

    Returns:
        The generated LibCST Module node for the test file.
    """
    body: list[cst.BaseStatement | cst.EmptyLine] = []

    body.append(cst.SimpleStatementLine([cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])]))
    body.append(cst.SimpleStatementLine([cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])]))
    body.append(cst.SimpleStatementLine([cst.Import(names=[cst.ImportAlias(name=cst.Name("sys"))])]))
    body.append(
        cst.SimpleStatementLine(
            [
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Attribute(value=cst.Name("sys"), attr=cst.Name("path")),
                            attr=cst.Name("insert"),
                        ),
                        args=[
                            cst.Arg(cst.Integer("0")),
                            cst.Arg(
                                cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(value=cst.Name("os"), attr=cst.Name("path")),
                                        attr=cst.Name("abspath"),
                                    ),
                                    args=[
                                        cst.Arg(
                                            cst.Call(
                                                func=cst.Attribute(
                                                    value=cst.Attribute(
                                                        value=cst.Name("os"),
                                                        attr=cst.Name("path"),
                                                    ),
                                                    attr=cst.Name("join"),
                                                ),
                                                args=[
                                                    cst.Arg(
                                                        cst.Call(
                                                            func=cst.Attribute(
                                                                value=cst.Attribute(
                                                                    value=cst.Name("os"),
                                                                    attr=cst.Name("path"),
                                                                ),
                                                                attr=cst.Name("dirname"),
                                                            ),
                                                            args=[cst.Arg(cst.Name("__file__"))],
                                                        )
                                                    ),
                                                    cst.Arg(cst.SimpleString("'../src'")),
                                                ],
                                            )
                                        )
                                    ],
                                )
                            ),
                        ],
                    )
                )
            ]
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

    if composable:
        default_url = get_test_base_url(spec, default_prefix="/v2")
        fixture_func = cst.FunctionDef(
            name=cst.Name("client"),
            params=cst.Parameters(),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(
                        [
                            cst.Return(
                                value=cst.Call(
                                    func=cst.Name("Client"),
                                    args=[
                                        cst.Arg(
                                            cst.Call(
                                                func=cst.Attribute(
                                                    value=cst.Name("os"),
                                                    attr=cst.Name("getenv"),
                                                ),
                                                args=[
                                                    cst.Arg(cst.SimpleString('"API_URL"')),
                                                    cst.Arg(cst.SimpleString(f'"{default_url}"')),
                                                ],
                                            )
                                        ),
                                        cst.Arg(
                                            keyword=cst.Name("api_key"),
                                            value=cst.SimpleString('"special-key"'),
                                        ),
                                    ],
                                )
                            )
                        ]
                    )
                ]
            ),
            decorators=[cst.Decorator(decorator=cst.Attribute(value=cst.Name("pytest"), attr=cst.Name("fixture")))],
        )
        body.append(fixture_func)
        body.append(cst.EmptyLine())

    if spec.paths:
        for path, path_item in spec.paths.items():
            if path.startswith("/"):
                for method in HTTP_METHODS:
                    operation = getattr(path_item, method, None)
                    if operation:
                        body.append(
                            emit_operation_test(
                                method,
                                path,
                                operation,
                                composable=composable,
                                spec=spec,
                            )
                        )
                        body.append(cst.EmptyLine())

    return build_cst_module(body)


def emit_api_tests(spec: OpenAPI) -> cst.Module:
    """Emit a `test_api.py` integration test module with resolved `API_URL` and `test_operations`.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated LibCST Module node for `test_api.py`.
    """
    default_url = get_test_base_url(spec, default_prefix="/v2")
    op_names: list[str] = []
    if spec.paths:
        for path, path_item in spec.paths.items():
            if path.startswith("/"):
                for method in HTTP_METHODS:
                    operation = getattr(path_item, method, None)
                    if operation:
                        raw_op_id = operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
                        op_names.append(sanitize_name(raw_op_id))
    if not op_names:
        op_names.append("default")

    ops_list_str = "[" + ", ".join(f'"{name}"' for name in op_names) + "]"
    code = f"""import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from client import Client

API_URL = os.getenv("API_URL", "{default_url}")
test_operations = {ops_list_str}


@pytest.fixture
def client():
    return Client(API_URL, api_key="special-key")


def test_api_client(client):
    assert client.base_url == API_URL
    assert len(test_operations) > 0


def test_generated_operations() -> None:
    assert len(test_operations) > 0
"""
    return cst.parse_module(code)
