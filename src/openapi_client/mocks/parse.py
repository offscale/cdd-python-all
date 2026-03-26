"""
Module for extracting OpenAPI Operations from FastAPI mock server ASTs.
"""

import libcst as cst
from openapi_client.models import OpenAPI, PathItem, Operation


class MockServerExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract mock server routes into OpenAPI Path/Operation structures.
    """

    def __init__(self, spec: OpenAPI):
        """Initialize MockServerExtractor with an OpenAPI spec."""
        self.spec = spec
        if not self.spec.paths:
            self.spec.paths = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """
        Extract operation based on FastAPI decorator (e.g., @app.get("/pets")).
        """
        name = node.name.value

        # Look for decorators like @app.get("/pets")
        if node.decorators:
            for decorator in node.decorators:
                if isinstance(decorator.decorator, cst.Call):
                    call = decorator.decorator
                    if isinstance(call.func, cst.Attribute) and isinstance(
                        call.func.value, cst.Name
                    ):
                        if call.func.value.value == "app":
                            method = call.func.attr.value
                            if method in ["get", "post", "put", "delete", "patch"]:
                                if call.args and isinstance(
                                    call.args[0].value, cst.SimpleString
                                ):
                                    path = call.args[0].value.evaluated_value

                                    if (
                                        self.spec.paths is not None
                                        and str(path) not in self.spec.paths
                                    ):
                                        self.spec.paths[str(path)] = PathItem(**{})  # type: ignore[call-arg]

                                    # Extract docstrings
                                    from openapi_client.docstrings.parse import (
                                        parse_docstring,
                                    )

                                    summary, description = parse_docstring(node)

                                    operation = Operation(operationId=name)
                                    if summary:
                                        operation.summary = summary
                                    if description:
                                        operation.description = description

                                    # Extract responses
                                    class ReturnExtractor(cst.CSTVisitor):
                                        """Visitor to find event stream responses."""

                                        def __init__(self):
                                            """Initialize ReturnExtractor."""
                                            self.has_event_stream = False

                                        def visit_Return(
                                            self, node: cst.Return
                                        ) -> None:
                                            """Check if the return is EventSourceResponse."""
                                            if isinstance(node.value, cst.Call):
                                                if isinstance(
                                                    node.value.func, cst.Name
                                                ):
                                                    if (
                                                        node.value.func.value
                                                        == "EventSourceResponse"
                                                    ):
                                                        self.has_event_stream = True

                                    ret_extractor = ReturnExtractor()
                                    node.visit(ret_extractor)
                                    if ret_extractor.has_event_stream:
                                        from openapi_client.models import (
                                            Response,
                                            MediaType,
                                        )

                                        operation.responses = {
                                            "200": Response(
                                                description="Server-sent events stream",
                                                content={
                                                    "text/event-stream": MediaType(**{})
                                                },
                                            )
                                        }

                                    if self.spec.paths is not None:
                                        setattr(
                                            self.spec.paths[str(path)],
                                            method,
                                            operation,
                                        )


def extract_mocks_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API operations from a parsed mock module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = MockServerExtractor(spec)
    module.visit(visitor)


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
