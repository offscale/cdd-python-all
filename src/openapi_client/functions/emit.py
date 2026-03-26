"""
Module for emitting Python functions (API client methods) from OpenAPI paths.
"""

from typing import List
import libcst as cst
from openapi_client.models import OpenAPI, Operation


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

    from openapi_client.functions.utils import get_annotation_for_schema

    query_statements = []
    has_query = False

    # Process query, header, path, cookie parameters
    if operation.parameters:
        has_query_params = any(
            getattr(p, "in_", getattr(p, "in", None)) == "query"
            for p in operation.parameters
        )
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
                param_name = param.name.replace("-", "_")

                # Determine type annotation
                schema_obj = getattr(param, "schema_", getattr(param, "schema", None))
                annotation_str = get_annotation_for_schema(schema_obj)

                if annotation_str.startswith("List") or annotation_str.startswith(
                    "Dict"
                ):
                    ann_node = cst.parse_expression(annotation_str)
                else:
                    ann_node = cst.Name(annotation_str)

                params_list.append(
                    cst.Param(
                        name=cst.Name(param_name),
                        annotation=cst.Annotation(ann_node),
                    )
                )

                # Process query params
                p_in = getattr(param, "in_", getattr(param, "in", None))
                if p_in == "query":
                    style = getattr(param, "style", "form")
                    delim = (
                        " "
                        if style == "spaceDelimited"
                        else ("|" if style == "pipeDelimited" else ",")
                    )

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
                                                            value=cst.Name(
                                                                "query_params"
                                                            ),
                                                            attr=cst.Name("append"),
                                                        ),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.BinaryOperation(
                                                                    left=cst.SimpleString(
                                                                        f"'{param.name}='"
                                                                    ),
                                                                    operator=cst.Add(),
                                                                    right=cst.Call(
                                                                        func=cst.Attribute(
                                                                            value=cst.SimpleString(
                                                                                f"'{delim}'"
                                                                            ),
                                                                            attr=cst.Name(
                                                                                "join"
                                                                            ),
                                                                        ),
                                                                        args=[
                                                                            cst.Arg(
                                                                                value=cst.Name(
                                                                                    param_name
                                                                                )
                                                                            )
                                                                        ],
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
                                                            value=cst.Name(
                                                                "query_params"
                                                            ),
                                                            attr=cst.Name("append"),
                                                        ),
                                                        args=[
                                                            cst.Arg(
                                                                value=cst.BinaryOperation(
                                                                    left=cst.SimpleString(
                                                                        f"'{param.name}='"
                                                                    ),
                                                                    operator=cst.Add(),
                                                                    right=cst.Call(
                                                                        func=cst.Name(
                                                                            "str"
                                                                        ),
                                                                        args=[
                                                                            cst.Arg(
                                                                                value=cst.Name(
                                                                                    param_name
                                                                                )
                                                                            )
                                                                        ],
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

    # Build the method body
    body_statements.extend(query_statements)

    url_value = cst.BinaryOperation(
        left=cst.Attribute(value=cst.Name("self"), attr=cst.Name("base_url")),
        operator=cst.Add(),
        right=cst.SimpleString(f'"{path}"'),
    )
    if has_query:
        url_value = cst.BinaryOperation(
            left=url_value,
            operator=cst.Add(),
            right=cst.BinaryOperation(
                left=cst.SimpleString("'?'"),
                operator=cst.Add(),
                right=cst.Call(
                    func=cst.Attribute(
                        value=cst.SimpleString("'&'"), attr=cst.Name("join")
                    ),
                    args=[cst.Arg(value=cst.Name("query_params"))],
                ),
            ),
        )

    body_statements.extend(
        [
            # Build URL (needs actual path variable interpolation later)
            cst.SimpleStatementLine(
                [
                    cst.Assign(
                        targets=[cst.AssignTarget(cst.Name("url"))],
                        value=url_value,
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
