"""
Module for emitting Python classes (Pydantic models) from OpenAPI schemas.
"""

from typing import Dict, List
import libcst as cst
from openapi_client.models import Schema, Reference, SchemaOrReference


def emit_class(name: str, schema: Schema) -> cst.ClassDef:
    """Emit a Pydantic BaseModel class from an OpenAPI Schema object."""
    class_body: List[cst.BaseStatement] = []

    from openapi_client.docstrings.emit import emit_class_docstring

    docstring = emit_class_docstring(schema)
    if docstring:
        class_body.append(docstring)

    if getattr(schema, "properties", None):
        for prop_name, prop_schema in schema.properties.items():  # type: ignore[union-attr]
            if isinstance(prop_schema, Reference):
                prop_type = "Any"  # Simplification for Reference
            else:
                prop_type = "Any"
                if getattr(prop_schema, "type", None) == "string":
                    prop_type = "str"
                elif getattr(prop_schema, "type", None) == "integer":
                    prop_type = "int"
                elif getattr(prop_schema, "type", None) == "number":
                    prop_type = "float"
                elif getattr(prop_schema, "type", None) == "boolean":
                    prop_type = "bool"

            class_body.append(
                cst.SimpleStatementLine(
                    [
                        cst.AnnAssign(
                            target=cst.Name(prop_name),
                            annotation=cst.Annotation(
                                cst.Subscript(
                                    value=cst.Name("Optional"),
                                    slice=[
                                        cst.SubscriptElement(
                                            cst.Index(cst.Name(prop_type))
                                        )
                                    ],
                                )
                            ),
                            value=cst.Name("None"),
                        )
                    ]
                )
            )

    if not class_body:
        class_body.append(cst.SimpleStatementLine([cst.Pass()]))

    return cst.ClassDef(
        name=cst.Name(name),
        bases=[cst.Arg(cst.Name("BaseModel"))],
        body=cst.IndentedBlock(body=class_body),  # type: ignore[arg-type]
    )


def emit_classes(schemas: Dict[str, SchemaOrReference]) -> List[cst.ClassDef]:
    """Emit a list of Pydantic BaseModel classes from a dictionary of OpenAPI Schema objects."""
    class_defs = []
    if schemas:
        for name, schema in schemas.items():
            if isinstance(schema, Schema) and getattr(schema, "type", None) == "object":
                class_defs.append(emit_class(name, schema))
    return class_defs


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
