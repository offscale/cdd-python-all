"""
Module for extracting OpenAPI Schemas from Python class ASTs (Pydantic models).
"""

import libcst as cst
from openapi_client.models import OpenAPI, Schema, Components


class ClassExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract Pydantic class definitions into OpenAPI Schemas.
    """

    def __init__(self, spec: OpenAPI):
        """Initialize ClassExtractor with an OpenAPI spec."""
        self.spec = spec
        if self.spec.components is None:
            self.spec.components = Components(schemas={})
        if getattr(self.spec.components, "schemas", None) is None:
            self.spec.components.schemas = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """
        Extract class structure to JSON Schema definitions inside components.schemas.
        """
        name = node.name.value
        if name == "Client":
            return  # Skip the main client class

        from openapi_client.docstrings.parse import parse_docstring

        summary, description = parse_docstring(node)

        schema = Schema(**{"ref": None})  # type: ignore
        schema.type = "object"
        schema.properties = {}
        if summary:
            schema.summary = summary
        if description:
            schema.description = description

        # Simple extraction of class attributes
        if isinstance(node.body, cst.IndentedBlock):
            for statement in node.body.body:
                if isinstance(statement, cst.SimpleStatementLine):
                    for body_element in statement.body:
                        if isinstance(body_element, cst.AnnAssign):
                            target = body_element.target
                            if isinstance(target, cst.Name):
                                prop_name = target.value
                                # Very basic type inference
                                prop_type = "string"  # default
                                if isinstance(
                                    body_element.annotation.annotation, cst.Subscript
                                ):
                                    # Optional[X]
                                    slice_elements = (
                                        body_element.annotation.annotation.slice
                                    )
                                    if slice_elements and isinstance(
                                        slice_elements[0].slice, cst.Index
                                    ):
                                        index_val = slice_elements[0].slice.value
                                        if isinstance(index_val, cst.Name):
                                            if index_val.value == "int":
                                                prop_type = "integer"
                                            elif index_val.value == "float":
                                                prop_type = "number"
                                            elif index_val.value == "bool":
                                                prop_type = "boolean"
                                if schema.properties is not None:
                                    s = Schema(**{"ref": None})  # type: ignore
                                    s.type = prop_type
                                    schema.properties[prop_name] = s

        if self.spec.components and self.spec.components.schemas is not None:
            self.spec.components.schemas[name] = schema


def extract_classes_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API schemas from a parsed module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = ClassExtractor(spec)
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
