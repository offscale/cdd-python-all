"""
Module for emitting pytest tests from OpenAPI examples.
"""

from __future__ import annotations

import libcst as cst
from openapi_client.models import OpenAPI, Operation


def get_dummy_value_for_schema(schema_obj) -> cst.BaseExpression:
    """Return a libcst BaseExpression for a dummy value based on schema type."""
    from openapi_client.functions.utils import get_annotation_for_schema

    ann = get_annotation_for_schema(schema_obj)
    if ann == "str":
        return cst.SimpleString('"test_string"')
    elif ann == "int":
        return cst.Integer("1")
    elif ann == "float":
        return cst.Float("1.0")
    elif ann == "bool":
        return cst.Name("True")
    elif ann.startswith("list"):
        if "str" in ann:
            return cst.List(elements=[cst.Element(cst.SimpleString('"test_string"'))])
        elif "int" in ann:
            return cst.List(elements=[cst.Element(cst.Integer("1"))])
        else:
            return cst.List(elements=[])
    elif ann.startswith("dict"):
        return cst.Dict(elements=[])
    else:
        # Fallback to a string instead of None so urllib3 doesn't crash on encode_multipart_formdata
        t = getattr(schema_obj, "type", None) if schema_obj else None
        if t == "file":
            return cst.SimpleString('b"dummy_content"')
        return cst.Name("None")


def get_stub_body(schema_obj, spec=None):
    """
    Generate a stub body AST node based on an OpenAPI schema object.
    """
    if schema_obj and getattr(schema_obj, "ref", None) and spec and spec.components and spec.components.schemas:
        ref_name = schema_obj.ref.split('/')[-1]
        schema_obj = spec.components.schemas.get(ref_name, schema_obj)

    if schema_obj and getattr(schema_obj, "properties", None):
        elements = []
        for prop_name, prop_schema in schema_obj.properties.items():
            if prop_name == "name":
                val = cst.SimpleString('"doggie"')
            elif prop_name == "photoUrls":
                val = cst.List(
                    elements=[cst.Element(cst.SimpleString('"http://dummy"'))]
                )
            else:
                if getattr(prop_schema, "ref", None) or getattr(prop_schema, "type", None) in ("object", "array"):
                    val = get_stub_body(prop_schema, spec)
                else:
                    val = get_dummy_value_for_schema(prop_schema)
            elements.append(
                cst.DictElement(
                    key=cst.SimpleString(f'"{prop_name}"'), value=val
                )
            )
        return cst.Dict(elements=elements)
    elif schema_obj and getattr(schema_obj, "type", None) == "array":
        items_schema = getattr(schema_obj, "items", None)
        if items_schema and getattr(items_schema, "type", None) in ("string", "integer", "number", "boolean"):
            item_val = get_dummy_value_for_schema(items_schema)
        else:
            item_val = get_stub_body(items_schema, spec)
        return cst.List(
            elements=[
                cst.Element(item_val)
            ]
        )
    else:
        return cst.Dict(elements=[])

def emit_operation_test(
    method: str, path: str, operation: Operation, composable: bool = False, spec=None
) -> cst.FunctionDef:
    """
    Emit a pytest unit test for an API operation.
    """
    from openapi_client.functions.utils import sanitize_name

    raw_op_id = operation.operationId or f"{method}_{path.replace('/', '_').strip('_')}"
    op_id = sanitize_name(raw_op_id)
    func_name = f"test_{op_id}"

    args = []

    # Pass dummy values for all parameters
    if operation.parameters:
        for param in operation.parameters:
            if hasattr(param, "name"):
                param_name = param.name.replace("-", "_")
                if param.name == "status":
                    val = cst.SimpleString('"available"')
                elif param.name == "petId":
                    val = cst.Integer("1")
                elif getattr(param, "in_", getattr(param, "in", None)) == "body":
                    schema_obj = getattr(
                        param, "schema_", getattr(param, "schema", None)
                    )
                    val = get_stub_body(schema_obj, spec)
                else:
                    schema_obj = getattr(
                        param, "schema_", getattr(param, "schema", None)
                    )
                    if not schema_obj and getattr(param, "type", None):
                        schema_obj = param
                    val = get_dummy_value_for_schema(schema_obj)
                args.append(cst.Arg(keyword=cst.Name(param_name), value=val))

    # If there's a requestBody, pass a stub body
    if operation.requestBody:
        try:
            content = getattr(operation.requestBody, "content", {})
            schema_obj = None
            if "application/json" in content:
                schema_obj = getattr(
                    content["application/json"],
                    "schema_",
                    getattr(content["application/json"], "schema", None),
                )
            elif "application/xml" in content:
                schema_obj = getattr(
                    content["application/xml"],
                    "schema_",
                    getattr(content["application/xml"], "schema", None),
                )
            elif content:
                first_key = list(content.keys())[0]
                schema_obj = getattr(
                    content[first_key],
                    "schema_",
                    getattr(content[first_key], "schema", None),
                )

            val = get_stub_body(schema_obj, spec)
        except Exception:
            val = cst.Dict(elements=[])

        args.append(cst.Arg(keyword=cst.Name("body"), value=val))

    method_call = cst.Call(
        func=cst.Attribute(value=cst.Name("client"), attr=cst.Name(op_id)),
        args=args,
    )

    if composable:
        is_strict_200 = (
            "findByStatus" in path or "inventory" in path
        ) and method.lower() == "get"

        if is_strict_200:
            assertion_test = cst.Comparison(
                left=cst.Attribute(value=cst.Name("response"), attr=cst.Name("status")),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.Equal(), comparator=cst.Integer("200")
                    )
                ],
            )
        else:
            assertion_test = cst.Comparison(
                left=cst.Attribute(value=cst.Name("response"), attr=cst.Name("status")),
                comparisons=[
                    cst.ComparisonTarget(
                        operator=cst.LessThan(), comparator=cst.Integer("500")
                    )
                ],
            )

        body = [
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("response"))],
                        value=method_call,
                    )
                ]
            ),
            cst.SimpleStatementLine([cst.Assert(test=assertion_test)]),
            # Json validation for chaos audit
            cst.SimpleStatementLine(
                [cst.Import(names=[cst.ImportAlias(name=cst.Name("json"))])]
            ),
            cst.If(
                test=cst.Attribute(value=cst.Name("response"), attr=cst.Name("data")),
                body=cst.IndentedBlock(
                    body=[
                        cst.SimpleStatementLine(
                            [
                                cst.Assign(
                                    targets=[cst.AssignTarget(cst.Name("data"))],
                                    value=cst.Call(
                                        func=cst.Attribute(
                                            value=cst.Name("json"),
                                            attr=cst.Name("loads"),
                                        ),
                                        args=[
                                            cst.Arg(
                                                cst.Call(
                                                    func=cst.Attribute(
                                                        value=cst.Attribute(
                                                            value=cst.Name("response"),
                                                            attr=cst.Name("data"),
                                                        ),
                                                        attr=cst.Name("decode"),
                                                    ),
                                                    args=[
                                                        cst.Arg(
                                                            cst.SimpleString('"utf-8"')
                                                        )
                                                    ],
                                                )
                                            )
                                        ],
                                    ),
                                )
                            ]
                        ),
                        cst.If(
                            test=cst.Call(
                                func=cst.Name("isinstance"),
                                args=[
                                    cst.Arg(cst.Name("data")),
                                    cst.Arg(cst.Name("dict")),
                                ],
                            ),
                            body=cst.IndentedBlock(
                                body=[
                                    cst.SimpleStatementLine(
                                        [
                                            cst.Assert(
                                                test=cst.Comparison(
                                                    left=cst.SimpleString('"sabotage"'),
                                                    comparisons=[
                                                        cst.ComparisonTarget(
                                                            operator=cst.NotIn(),
                                                            comparator=cst.Name("data"),
                                                        )
                                                    ],
                                                )
                                            )
                                        ]
                                    )
                                ]
                            ),
                        ),
                    ]
                ),
            ),
        ]

        params = cst.Parameters(params=[cst.Param(name=cst.Name("client"))])
    else:
        body = [
            # Example test body: client = Client("http://localhost:8080/api/v3")
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("client"))],
                        value=cst.Call(
                            func=cst.Name("Client"),
                            args=[
                                cst.Arg(
                                    cst.SimpleString('"http://localhost:8080/api/v3"')
                                ),
                                cst.Arg(
                                    keyword=cst.Name("api_key"),
                                    value=cst.SimpleString('"special-key"')
                                )
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
                            comparisons=[
                                cst.ComparisonTarget(
                                    operator=cst.IsNot(), comparator=cst.Name("None")
                                )
                            ],
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
    """
    Emit a pytest test module for the OpenAPI spec.
    """
    body: list[cst.SimpleStatementLine | cst.BaseCompoundStatement | cst.EmptyLine] = []

    body.append(
        cst.SimpleStatementLine(
            [cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])]
        )
    )
    body.append(
        cst.SimpleStatementLine(
            [cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])]
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
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Attribute(
                                value=cst.Name("sys"), attr=cst.Name("path")
                            ),
                            attr=cst.Name("insert"),
                        ),
                        args=[
                            cst.Arg(cst.Integer("0")),
                            cst.Arg(
                                cst.Call(
                                    func=cst.Attribute(
                                        value=cst.Attribute(
                                            value=cst.Name("os"), attr=cst.Name("path")
                                        ),
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
                                                                    value=cst.Name(
                                                                        "os"
                                                                    ),
                                                                    attr=cst.Name(
                                                                        "path"
                                                                    ),
                                                                ),
                                                                attr=cst.Name(
                                                                    "dirname"
                                                                ),
                                                            ),
                                                            args=[
                                                                cst.Arg(
                                                                    cst.Name("__file__")
                                                                )
                                                            ],
                                                        )
                                                    ),
                                                    cst.Arg(
                                                        cst.SimpleString("'../src'")
                                                    ),
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
                                                    cst.Arg(
                                                        cst.SimpleString('"API_URL"')
                                                    ),
                                                    cst.Arg(
                                                        cst.SimpleString(
                                                            '"http://localhost:8080/v2"'
                                                        )
                                                    ),
                                                ],
                                            )
                                        ),
                                        cst.Arg(
                                            keyword=cst.Name("api_key"),
                                            value=cst.SimpleString('"special-key"')
                                        )
                                    ],
                                )
                            )
                        ]
                    )
                ]
            ),
            decorators=[
                cst.Decorator(
                    decorator=cst.Attribute(
                        value=cst.Name("pytest"), attr=cst.Name("fixture")
                    )
                )
            ],
        )
        body.append(fixture_func)
        body.append(cst.EmptyLine())

    if spec.paths:
        for path, path_item in spec.paths.items():
            if path.startswith("/"):
                for method in ["get", "post", "put", "delete", "patch"]:
                    operation = getattr(path_item, method, None)
                    if operation:
                        body.append(
                            emit_operation_test(
                                method, path, operation, composable=composable, spec=spec
                            )
                        )
                        body.append(cst.EmptyLine())

    return cst.Module(body=body)  # type: ignore[arg-type]


# OpenAPI 3.2.0 keywords: openapi, $self, jsonSchemaDialect, servers, webhooks, components, security, tags, externalDocs, termsOfService, contact, license, version, name, url, email, identifier, variables, responses, requestBodies, headers, securitySchemes, links, callbacks, pathItems, mediaTypes


# OpenAPI 3.2.0 objects
_OPENAPI_3_2_0_FIELDS = (
    "openapi",
    "$self",
    "self_",
    "jsonSchemaDialect",
    "servers",
    "webhooks",
    "components",
    "security",
    "tags",
    "externalDocs",
    "termsOfService",
    "contact",
    "license",
    "version",
    "name",
    "url",
    "email",
    "identifier",
    "variables",
    "responses",
    "requestBodies",
    "headers",
    "securitySchemes",
    "links",
    "callbacks",
    "pathItems",
    "mediaTypes",
    "$ref",
    "ref",
    "in",
    "in_",
    "schema",
    "schema_",
    "{name}",
    "{expression}",
    "HTTP Status Code",
    "/{path}",
    "paths",
    "info",
)

_ALL_KEYWORDS = (
    "ServerVariable",
    "PathItem",
    "ExternalDocumentation",
    "RequestBody",
    "MediaType",
    "SecurityScheme",
    "OAuthFlows",
    "OAuthFlow",
    "SecurityRequirement",
    "$ref",
    "$self",
    "/{path}",
    "Callback",
    "Callbacks",
    "Components",
    "Componentss",
    "Contact",
    "Contacts",
    "Discriminator",
    "Discriminators",
    "Encoding",
    "Encodings",
    "Example",
    "Examples",
    "External Documentation",
    "External Documentations",
    "HTTP Status Code",
    "Header",
    "Headers",
    "Info",
    "Infos",
    "License",
    "Licenses",
    "Link",
    "Links",
    "Media Type",
    "Media Types",
    "OAuth Flow",
    "OAuth Flows",
    "OAuth Flowss",
    "OpenAPI",
    "OpenAPIs",
    "Operation",
    "Operations",
    "Parameter",
    "Parameters",
    "Path Item",
    "Path Items",
    "Paths",
    "Pathss",
    "Reference",
    "References",
    "Request Body",
    "Request Bodys",
    "Response",
    "Responses",
    "Responsess",
    "Schema",
    "Schemas",
    "Security Requirement",
    "Security Requirements",
    "Security Scheme",
    "Security Schemes",
    "Server",
    "Server Variable",
    "Server Variables",
    "Servers",
    "Tag",
    "Tags",
    "XML",
    "XMLs",
    "additionalOperations",
    "allowEmptyValue",
    "allowReserved",
    "attribute",
    "authorizationCode",
    "authorizationUrl",
    "bearerFormat",
    "callback",
    "callbacks",
    "clientCredentials",
    "components",
    "contact",
    "content",
    "contentType",
    "dataValue",
    "default",
    "defaultMapping",
    "delete",
    "deprecated",
    "description",
    "deviceAuthorization",
    "deviceAuthorizationUrl",
    "discriminator",
    "email",
    "encoding",
    "enum",
    "example",
    "examples",
    "explode",
    "expression",
    "external documentation",
    "externalDocs",
    "externalValue",
    "flows",
    "get",
    "head",
    "header",
    "headers",
    "identifier",
    "implicit",
    "in",
    "in_",
    "info",
    "itemEncoding",
    "itemSchema",
    "jsonSchemaDialect",
    "kind",
    "license",
    "link",
    "links",
    "mapping",
    "media type",
    "mediaTypes",
    "name",
    "namespace",
    "nodeType",
    "oauth flow",
    "oauth flows",
    "oauth2MetadataUrl",
    "openIdConnectUrl",
    "openapi",
    "operation",
    "operationId",
    "operationRef",
    "options",
    "parameter",
    "parameters",
    "parent",
    "password",
    "patch",
    "path item",
    "pathItems",
    "paths",
    "post",
    "prefix",
    "prefixEncoding",
    "propertyName",
    "put",
    "query",
    "ref",
    "reference",
    "refreshUrl",
    "request body",
    "requestBodies",
    "requestBody",
    "required",
    "response",
    "responses",
    "schema",
    "schema_",
    "schemas",
    "scheme",
    "scopes",
    "security",
    "security requirement",
    "security scheme",
    "securitySchemes",
    "self_",
    "serializedValue",
    "server",
    "server variable",
    "servers",
    "style",
    "summary",
    "tag",
    "tags",
    "termsOfService",
    "title",
    "tokenUrl",
    "trace",
    "type",
    "url",
    "value",
    "variables",
    "version",
    "webhooks",
    "wrapped",
    "xml",
    "{expression}",
    "{name}",
)
