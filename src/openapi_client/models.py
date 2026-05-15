"""OpenAPI 3.2.0 Pydantic models."""

from __future__ import annotations

from typing import Any, Union
from pydantic import BaseModel, ConfigDict, Field


class OpenAPIBase(BaseModel):
    """OpenAPI OpenAPIBase model."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Contact(OpenAPIBase):
    """OpenAPI Contact model."""

    name: str | None = None
    url: str | None = None
    email: str | None = None


class License(OpenAPIBase):
    """OpenAPI License model."""

    name: str
    identifier: str | None = None
    url: str | None = None


class Info(OpenAPIBase):
    """OpenAPI Info model."""

    title: str
    summary: str | None = None
    description: str | None = None
    termsOfService: str | None = None
    contact: Contact | None = None
    license: License | None = None
    version: str


class ServerVariable(OpenAPIBase):
    """OpenAPI ServerVariable model."""

    enum: list[str] | None = None
    default: str
    description: str | None = None


class Server(OpenAPIBase):
    """OpenAPI Server model."""

    url: str
    description: str | None = None
    name: str | None = None
    variables: dict[str, ServerVariable] | None = None


class ExternalDocumentation(OpenAPIBase):
    """OpenAPI ExternalDocumentation model."""

    description: str | None = None
    url: str


class Tag(OpenAPIBase):
    """OpenAPI Tag model."""

    name: str
    summary: str | None = None
    description: str | None = None
    externalDocs: ExternalDocumentation | None = None
    parent: str | None = None
    kind: str | None = None


class Discriminator(OpenAPIBase):
    """OpenAPI Discriminator model."""

    propertyName: str
    mapping: dict[str, str] | None = None
    defaultMapping: str | None = None


class XML(OpenAPIBase):
    """OpenAPI XML model."""

    nodeType: str | None = None
    name: str | None = None
    namespace: str | None = None
    prefix: str | None = None
    attribute: bool | None = None
    wrapped: bool | None = None


class Reference(OpenAPIBase):
    """OpenAPI Reference model."""

    ref: str = Field(..., alias="$ref")
    summary: str | None = None
    description: str | None = None


class Schema(OpenAPIBase):
    """OpenAPI Schema model."""

    title: str | None = None
    summary: str | None = None
    description: str | None = None
    discriminator: Discriminator | None = None
    xml: XML | None = None
    externalDocs: ExternalDocumentation | None = None
    example: Any | None = None
    ref: str | None = Field(None, alias="$ref")
    type: str | list[str] | None = None
    properties: dict[str, SchemaOrReference] | None = None
    items: SchemaOrReference | list[SchemaOrReference] | None = None
    allOf: list[SchemaOrReference] | None = None
    anyOf: list[SchemaOrReference] | None = None
    oneOf: list[SchemaOrReference] | None = None
    default: Any | None = None
    multipleOf: float | None = None
    maximum: float | None = None
    exclusiveMaximum: bool | None = None
    minimum: float | None = None
    exclusiveMinimum: bool | None = None
    maxLength: int | None = None
    minLength: int | None = None
    pattern: str | None = None
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool | None = None
    maxProperties: int | None = None
    minProperties: int | None = None
    required: list[str] | None = None
    enum: list[Any] | None = None
    readOnly: bool | None = None
    # We allow extra fields since it supports full JSON Schema draft 2020-12


class Example(OpenAPIBase):
    """OpenAPI Example model."""

    summary: str | None = None
    description: str | None = None
    dataValue: Any | None = None
    serializedValue: str | None = None
    externalValue: str | None = None
    value: Any | None = None


class Link(OpenAPIBase):
    """OpenAPI Link model."""

    operationRef: str | None = None
    operationId: str | None = None
    parameters: dict[str, Any] | None = None
    requestBody: Any | None = None
    description: str | None = None
    server: Server | None = None


class Header(OpenAPIBase):
    """OpenAPI Header model."""

    description: str | None = None
    required: bool | None = None
    deprecated: bool | None = None
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    type: str | None = None
    format: str | None = None
    items: SchemaOrReference | list[SchemaOrReference] | None = None
    collectionFormat: str | None = None
    default: Any | None = None
    maximum: float | None = None
    exclusiveMaximum: bool | None = None
    minimum: float | None = None
    exclusiveMinimum: bool | None = None
    maxLength: int | None = None
    minLength: int | None = None
    pattern: str | None = None
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool | None = None
    enum: list[Any] | None = None
    multipleOf: float | None = None


class Encoding(OpenAPIBase):
    """OpenAPI Encoding model."""

    contentType: str | None = None
    headers: dict[str, Header | Reference] | None = None
    encoding: dict[str, Encoding] | None = None
    prefixEncoding: list[Encoding] | None = None
    itemEncoding: Encoding | None = None
    style: str | None = None
    explode: bool | None = None
    allowReserved: bool | None = None


class MediaType(OpenAPIBase):
    """OpenAPI MediaType model."""

    schema_: SchemaOrReference | None = Field(None, alias="schema")
    itemSchema: SchemaOrReference | None = None
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    encoding: dict[str, Encoding] | None = None
    prefixEncoding: list[Encoding] | None = None
    itemEncoding: Encoding | None = None


class RequestBody(OpenAPIBase):
    """OpenAPI RequestBody model."""

    description: str | None = None
    content: dict[str, MediaType | Reference]
    required: bool | None = None


class Parameter(OpenAPIBase):
    """OpenAPI Parameter model."""

    name: str
    in_: str = Field(..., alias="in")
    description: str | None = None
    required: bool | None = None
    deprecated: bool | None = None
    allowEmptyValue: bool | None = None
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    style: str | None = None
    explode: bool | None = None
    allowReserved: bool | None = None
    schema_: SchemaOrReference | None = Field(None, alias="schema")
    content: dict[str, MediaType | Reference] | None = None
    type: str | None = None
    format: str | None = None
    collectionFormat: str | None = None
    default: Any | None = None
    maximum: float | None = None
    exclusiveMaximum: bool | None = None
    minimum: float | None = None
    exclusiveMinimum: bool | None = None
    maxLength: int | None = None
    minLength: int | None = None
    pattern: str | None = None
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool | None = None
    enum: list[Any] | None = None
    multipleOf: float | None = None
    items: SchemaOrReference | list[SchemaOrReference] | None = None


class Response(OpenAPIBase):
    """OpenAPI Response model."""

    summary: str | None = None
    description: str | None = None
    headers: dict[str, Header | Reference] | None = None
    content: dict[str, MediaType | Reference] | None = None
    links: dict[str, Link | Reference] | None = None


class Responses(OpenAPIBase):
    """OpenAPI Responses model."""

    default: Response | Reference | None = None
    # the rest are HTTP status codes as string keys, so we allow extra properties


class OAuthFlow(OpenAPIBase):
    """OpenAPI OAuthFlow model."""

    authorizationUrl: str | None = None
    tokenUrl: str | None = None
    refreshUrl: str | None = None
    scopes: dict[str, str]


class OAuthFlows(OpenAPIBase):
    """OpenAPI OAuthFlows model."""

    implicit: OAuthFlow | None = None
    password: OAuthFlow | None = None
    clientCredentials: OAuthFlow | None = None
    authorizationCode: OAuthFlow | None = None
    deviceAuthorization: OAuthFlow | None = None


class SecurityScheme(OpenAPIBase):
    """OpenAPI SecurityScheme model."""

    type: str
    description: str | None = None
    name: str | None = None
    in_: str | None = Field(None, alias="in")
    scheme: str | None = None
    bearerFormat: str | None = None
    flows: OAuthFlows | None = None
    openIdConnectUrl: str | None = None
    oauth2MetadataUrl: str | None = None
    deprecated: bool | None = None
    flow: str | None = None
    authorizationUrl: str | None = None
    tokenUrl: str | None = None
    scopes: dict[str, str] | None = None


class Callback(OpenAPIBase):
    """OpenAPI Callback model."""

    pass  # A map of expressions to PathItem, allow extra


class Operation(OpenAPIBase):
    """OpenAPI Operation model."""

    tags: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    externalDocs: ExternalDocumentation | None = None
    operationId: str | None = None
    parameters: list[Parameter | Reference] | None = None
    requestBody: RequestBody | Reference | None = None
    responses: dict[str, Response | Reference] | None = None
    callbacks: dict[str, Callback | Reference] | None = None
    deprecated: bool | None = None
    security: list[dict[str, list[str]]] | None = None
    servers: list[Server] | None = None
    consumes: list[str] | None = None
    produces: list[str] | None = None
    schemes: list[str] | None = None


class PathItem(OpenAPIBase):
    """OpenAPI PathItem model."""

    ref: str | None = Field(None, alias="$ref")
    summary: str | None = None
    description: str | None = None
    get: Operation | None = None
    put: Operation | None = None
    post: Operation | None = None
    delete: Operation | None = None
    options: Operation | None = None
    head: Operation | None = None
    patch: Operation | None = None
    trace: Operation | None = None
    query: Operation | None = None
    additionalOperations: dict[str, Operation] | None = None
    servers: list[Server] | None = None
    parameters: list[Parameter | Reference] | None = None


class Paths(OpenAPIBase):
    """OpenAPI Paths model."""

    # A map of paths to PathItem, allow extra properties
    pass


class Components(OpenAPIBase):
    """OpenAPI Components model."""

    schemas: dict[str, SchemaOrReference] | None = None
    responses: dict[str, Response | Reference] | None = None
    parameters: dict[str, Parameter | Reference] | None = None
    examples: dict[str, Example | Reference] | None = None
    requestBodies: dict[str, RequestBody | Reference] | None = None
    headers: dict[str, Header | Reference] | None = None
    securitySchemes: dict[str, SecurityScheme | Reference] | None = None
    links: dict[str, Link | Reference] | None = None
    callbacks: dict[str, Callback | Reference] | None = None
    pathItems: dict[str, PathItem] | None = None
    mediaTypes: dict[str, MediaType | Reference] | None = None


class OpenAPI(OpenAPIBase):
    """OpenAPI OpenAPI model."""

    openapi: str | None = None
    swagger: str | None = None
    self_: str | None = Field(None, alias="$self")
    info: Info
    jsonSchemaDialect: str | None = None
    servers: list[Server] | None = None
    paths: dict[str, PathItem] | None = None
    webhooks: dict[str, PathItem] | None = None
    components: Components | None = None
    security: list[dict[str, list[str]]] | None = None
    tags: list[Tag] | None = None
    externalDocs: ExternalDocumentation | None = None
    host: str | None = None
    basePath: str | None = None
    schemes: list[str] | None = None
    consumes: list[str] | None = None
    produces: list[str] | None = None
    definitions: dict[str, SchemaOrReference] | None = None
    parameters: dict[str, Parameter | Reference] | None = None
    responses: dict[str, Response | Reference] | None = None
    securityDefinitions: dict[str, SecurityScheme | Reference] | None = None


SchemaOrReference = Union[Schema, Reference]

# Rebuild models due to forward references
for model in list(locals().values()):
    if isinstance(model, type) and issubclass(model, BaseModel) and model != BaseModel:
        if hasattr(model, "model_rebuild"):
            model.model_rebuild()
        elif hasattr(model, "update_forward_refs"):  # pragma: no cover
            model.update_forward_refs()  # pragma: no cover
