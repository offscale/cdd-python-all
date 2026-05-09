"""OpenAPI 3.2.0 Pydantic models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class OpenAPIBase(BaseModel):
    """OpenAPI OpenAPIBase model."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Contact(OpenAPIBase):
    """OpenAPI Contact model."""

    name: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None


class License(OpenAPIBase):
    """OpenAPI License model."""

    name: str
    identifier: Optional[str] = None
    url: Optional[str] = None


class Info(OpenAPIBase):
    """OpenAPI Info model."""

    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    termsOfService: Optional[str] = None
    contact: Optional[Contact] = None
    license: Optional[License] = None
    version: str


class ServerVariable(OpenAPIBase):
    """OpenAPI ServerVariable model."""

    enum: Optional[List[str]] = None
    default: str
    description: Optional[str] = None


class Server(OpenAPIBase):
    """OpenAPI Server model."""

    url: str
    description: Optional[str] = None
    name: Optional[str] = None
    variables: Optional[Dict[str, ServerVariable]] = None


class ExternalDocumentation(OpenAPIBase):
    """OpenAPI ExternalDocumentation model."""

    description: Optional[str] = None
    url: str


class Tag(OpenAPIBase):
    """OpenAPI Tag model."""

    name: str
    summary: Optional[str] = None
    description: Optional[str] = None
    externalDocs: Optional[ExternalDocumentation] = None
    parent: Optional[str] = None
    kind: Optional[str] = None


class Discriminator(OpenAPIBase):
    """OpenAPI Discriminator model."""

    propertyName: str
    mapping: Optional[Dict[str, str]] = None
    defaultMapping: Optional[str] = None


class XML(OpenAPIBase):
    """OpenAPI XML model."""

    nodeType: Optional[str] = None
    name: Optional[str] = None
    namespace: Optional[str] = None
    prefix: Optional[str] = None
    attribute: Optional[bool] = None
    wrapped: Optional[bool] = None


class Reference(OpenAPIBase):
    """OpenAPI Reference model."""

    ref: str = Field(..., alias="$ref")
    summary: Optional[str] = None
    description: Optional[str] = None


class Schema(OpenAPIBase):
    """OpenAPI Schema model."""

    title: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    discriminator: Optional[Discriminator] = None
    xml: Optional[XML] = None
    externalDocs: Optional[ExternalDocumentation] = None
    example: Optional[Any] = None
    ref: Optional[str] = Field(None, alias="$ref")
    type: Optional[Union[str, List[str]]] = None
    properties: Optional[Dict[str, SchemaOrReference]] = None
    items: Optional[Union[SchemaOrReference, List[SchemaOrReference]]] = None
    allOf: Optional[List[SchemaOrReference]] = None
    anyOf: Optional[List[SchemaOrReference]] = None
    oneOf: Optional[List[SchemaOrReference]] = None
    # We allow extra fields since it supports full JSON Schema draft 2020-12


class Example(OpenAPIBase):
    """OpenAPI Example model."""

    summary: Optional[str] = None
    description: Optional[str] = None
    dataValue: Optional[Any] = None
    serializedValue: Optional[str] = None
    externalValue: Optional[str] = None
    value: Optional[Any] = None


class Link(OpenAPIBase):
    """OpenAPI Link model."""

    operationRef: Optional[str] = None
    operationId: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    requestBody: Optional[Any] = None
    description: Optional[str] = None
    server: Optional[Server] = None


class Header(OpenAPIBase):
    """OpenAPI Header model."""

    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    example: Optional[Any] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None


class Encoding(OpenAPIBase):
    """OpenAPI Encoding model."""

    contentType: Optional[str] = None
    headers: Optional[Dict[str, Union[Header, Reference]]] = None
    encoding: Optional[Dict[str, Encoding]] = None
    prefixEncoding: Optional[List[Encoding]] = None
    itemEncoding: Optional[Encoding] = None
    style: Optional[str] = None
    explode: Optional[bool] = None
    allowReserved: Optional[bool] = None


class MediaType(OpenAPIBase):
    """OpenAPI MediaType model."""

    schema_: Optional[SchemaOrReference] = Field(None, alias="schema")
    itemSchema: Optional[SchemaOrReference] = None
    example: Optional[Any] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None
    encoding: Optional[Dict[str, Encoding]] = None
    prefixEncoding: Optional[List[Encoding]] = None
    itemEncoding: Optional[Encoding] = None


class RequestBody(OpenAPIBase):
    """OpenAPI RequestBody model."""

    description: Optional[str] = None
    content: Dict[str, Union[MediaType, Reference]]
    required: Optional[bool] = None


class Parameter(OpenAPIBase):
    """OpenAPI Parameter model."""

    name: str
    in_: str = Field(..., alias="in")
    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    allowEmptyValue: Optional[bool] = None
    example: Optional[Any] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None
    style: Optional[str] = None
    explode: Optional[bool] = None
    allowReserved: Optional[bool] = None
    schema_: Optional[SchemaOrReference] = Field(None, alias="schema")
    content: Optional[Dict[str, Union[MediaType, Reference]]] = None


class Response(OpenAPIBase):
    """OpenAPI Response model."""

    summary: Optional[str] = None
    description: Optional[str] = None
    headers: Optional[Dict[str, Union[Header, Reference]]] = None
    content: Optional[Dict[str, Union[MediaType, Reference]]] = None
    links: Optional[Dict[str, Union[Link, Reference]]] = None


class Responses(OpenAPIBase):
    """OpenAPI Responses model."""

    default: Optional[Union[Response, Reference]] = None
    # the rest are HTTP status codes as string keys, so we allow extra properties


class OAuthFlow(OpenAPIBase):
    """OpenAPI OAuthFlow model."""

    authorizationUrl: Optional[str] = None
    tokenUrl: Optional[str] = None
    refreshUrl: Optional[str] = None
    scopes: Dict[str, str]


class OAuthFlows(OpenAPIBase):
    """OpenAPI OAuthFlows model."""

    implicit: Optional[OAuthFlow] = None
    password: Optional[OAuthFlow] = None
    clientCredentials: Optional[OAuthFlow] = None
    authorizationCode: Optional[OAuthFlow] = None
    deviceAuthorization: Optional[OAuthFlow] = None


class SecurityScheme(OpenAPIBase):
    """OpenAPI SecurityScheme model."""

    type: str
    description: Optional[str] = None
    name: Optional[str] = None
    in_: Optional[str] = Field(None, alias="in")
    scheme: Optional[str] = None
    bearerFormat: Optional[str] = None
    flows: Optional[OAuthFlows] = None
    openIdConnectUrl: Optional[str] = None
    oauth2MetadataUrl: Optional[str] = None
    deprecated: Optional[bool] = None


class Callback(OpenAPIBase):
    """OpenAPI Callback model."""

    pass  # A map of expressions to PathItem, allow extra


class Operation(OpenAPIBase):
    """OpenAPI Operation model."""

    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    externalDocs: Optional[ExternalDocumentation] = None
    operationId: Optional[str] = None
    parameters: Optional[List[Union[Parameter, Reference]]] = None
    requestBody: Optional[Union[RequestBody, Reference]] = None
    responses: Optional[Dict[str, Union[Response, Reference]]] = None
    callbacks: Optional[Dict[str, Union[Callback, Reference]]] = None
    deprecated: Optional[bool] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    servers: Optional[List[Server]] = None


class PathItem(OpenAPIBase):
    """OpenAPI PathItem model."""

    ref: Optional[str] = Field(None, alias="$ref")
    summary: Optional[str] = None
    description: Optional[str] = None
    get: Optional[Operation] = None
    put: Optional[Operation] = None
    post: Optional[Operation] = None
    delete: Optional[Operation] = None
    options: Optional[Operation] = None
    head: Optional[Operation] = None
    patch: Optional[Operation] = None
    trace: Optional[Operation] = None
    query: Optional[Operation] = None
    additionalOperations: Optional[Dict[str, Operation]] = None
    servers: Optional[List[Server]] = None
    parameters: Optional[List[Union[Parameter, Reference]]] = None


class Paths(OpenAPIBase):
    """OpenAPI Paths model."""

    # A map of paths to PathItem, allow extra properties
    pass


class Components(OpenAPIBase):
    """OpenAPI Components model."""

    schemas: Optional[Dict[str, SchemaOrReference]] = None
    responses: Optional[Dict[str, Union[Response, Reference]]] = None
    parameters: Optional[Dict[str, Union[Parameter, Reference]]] = None
    examples: Optional[Dict[str, Union[Example, Reference]]] = None
    requestBodies: Optional[Dict[str, Union[RequestBody, Reference]]] = None
    headers: Optional[Dict[str, Union[Header, Reference]]] = None
    securitySchemes: Optional[Dict[str, Union[SecurityScheme, Reference]]] = None
    links: Optional[Dict[str, Union[Link, Reference]]] = None
    callbacks: Optional[Dict[str, Union[Callback, Reference]]] = None
    pathItems: Optional[Dict[str, PathItem]] = None
    mediaTypes: Optional[Dict[str, Union[MediaType, Reference]]] = None


class OpenAPI(OpenAPIBase):
    """OpenAPI OpenAPI model."""

    openapi: str
    self_: Optional[str] = Field(None, alias="$self")
    info: Info
    jsonSchemaDialect: Optional[str] = None
    servers: Optional[List[Server]] = None
    paths: Optional[Dict[str, PathItem]] = None
    webhooks: Optional[Dict[str, PathItem]] = None
    components: Optional[Components] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    tags: Optional[List[Tag]] = None
    externalDocs: Optional[ExternalDocumentation] = None


SchemaOrReference = Union[Schema, Reference]

# Rebuild models due to forward references
for model in list(locals().values()):
    if isinstance(model, type) and issubclass(model, BaseModel) and model != BaseModel:
        model.model_rebuild()
