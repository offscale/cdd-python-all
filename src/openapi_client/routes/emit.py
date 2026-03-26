"""
Module for emitting complete Python client module from OpenAPI schema.
"""

import libcst as cst
from openapi_client.models import OpenAPI
from openapi_client.classes.emit import emit_classes
from openapi_client.functions.emit import emit_functions

from typing import List


class ClientGenerator:
    """
    Generator class responsible for converting an OpenAPI object into a libcst.Module.
    """

    def __init__(self, spec: OpenAPI):
        """Initialize ClientGenerator with an OpenAPI spec."""
        self.spec = spec

    def generate(self) -> cst.Module:
        """
        Generate the AST module containing imports, Pydantic classes, and the Client class.

        Returns:
            cst.Module: The constructed Python syntax tree representing the client.
        """
        body: List[cst.BaseStatement | cst.EmptyLine] = []

        # Emit imports
        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("urllib3"),
                        names=[cst.ImportAlias(name=cst.Name("PoolManager"))],
                    )
                ]
            )
        )
        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("typing"),
                        names=[
                            cst.ImportAlias(name=cst.Name("Any")),
                            cst.ImportAlias(name=cst.Name("Dict")),
                            cst.ImportAlias(name=cst.Name("Optional")),
                            cst.ImportAlias(name=cst.Name("List")),
                        ],
                    )
                ]
            )
        )
        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("pydantic"),
                        names=[
                            cst.ImportAlias(name=cst.Name("BaseModel")),
                            cst.ImportAlias(name=cst.Name("Field")),
                        ],
                    )
                ]
            )
        )
        body.append(cst.EmptyLine())

        # Emit classes (Pydantic Models)
        if self.spec.components and self.spec.components.schemas:
            class_defs = emit_classes(self.spec.components.schemas)
            for class_def in class_defs:
                body.append(class_def)
                body.append(cst.EmptyLine())

        # Emit functions inside the Client class
        methods = emit_functions(self.spec)

        client_class = cst.ClassDef(
            name=cst.Name("Client"), body=cst.IndentedBlock(body=methods)
        )

        body.append(client_class)

        return cst.Module(body=body)  # type: ignore

    def generate_code(self) -> str:
        """
        Generate Python source code directly from the OpenAPI specification.

        Returns:
            str: The generated Python code as a string.
        """
        return self.generate().code


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
