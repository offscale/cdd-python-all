"""Module for parsing an existing CLI application and updating an OpenAPI specification."""

import libcst as cst
from openapi_client.models import OpenAPI, Operation, Parameter, Schema


class CLIExtractor(cst.CSTVisitor):
    """Visitor for extracting CLI arguments into an OpenAPI spec."""

    def __init__(self, spec: OpenAPI):
        """Initialize the extractor."""
        self.spec = spec
        self.current_op_id = None
        self.current_op = None

    def visit_Call(self, node: cst.Call):
        """Visit call nodes to extract argparse details."""
        if (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "add_parser"
        ):
            if node.args and isinstance(node.args[0].value, cst.SimpleString):
                op_id = node.args[0].value.value.strip("\"'")
                self.current_op_id = op_id

                # Try to find an existing operation in spec, or create a mock one
                # Actually mapping op_id back to path/method is hard without prior knowledge,
                # but we can try to guess or just let it update existing ones.
                found = False
                if self.spec.paths:
                    for path, path_item in self.spec.paths.items():
                        for method in ["get", "post", "put", "delete", "patch"]:
                            op = getattr(path_item, method, None)
                            if op and op.operationId == op_id:
                                self.current_op = op
                                found = True
                                break
                        if found:
                            break

                if self.current_op:
                    for arg in node.args:
                        if getattr(arg.keyword, "value", None) == "help" and isinstance(
                            arg.value, cst.SimpleString
                        ):
                            self.current_op.summary = arg.value.value.strip("\"'")

        elif (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "add_argument"
        ):
            if (
                self.current_op
                and node.args
                and isinstance(node.args[0].value, cst.SimpleString)
            ):
                arg_name = node.args[0].value.value.strip("\"'")
                if arg_name.startswith("--"):
                    p_name = arg_name[2:]

                    p_desc = ""
                    for arg in node.args:
                        if getattr(arg.keyword, "value", None) == "help" and isinstance(
                            arg.value, cst.SimpleString
                        ):
                            p_desc = arg.value.value.strip("\"'")

                    # Update parameter description
                    if self.current_op.parameters:
                        for p in self.current_op.parameters:
                            if getattr(p, "name", "").replace("-", "_") == p_name:
                                p.description = p_desc


def extract_cli_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract CLI information from an AST module into an OpenAPI spec."""
    extractor = CLIExtractor(spec)
    module.visit(extractor)


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
