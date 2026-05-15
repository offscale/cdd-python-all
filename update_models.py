import re

with open("src/openapi_client/models.py", "r") as f:
    content = f.read()

# Add to Schema
content = content.replace(
    'oneOf: list[SchemaOrReference] | None = None',
    'oneOf: list[SchemaOrReference] | None = None\n    default: Any | None = None\n    multipleOf: float | None = None\n    maximum: float | None = None\n    exclusiveMaximum: bool | None = None\n    minimum: float | None = None\n    exclusiveMinimum: bool | None = None\n    maxLength: int | None = None\n    minLength: int | None = None\n    pattern: str | None = None\n    maxItems: int | None = None\n    minItems: int | None = None\n    uniqueItems: bool | None = None\n    maxProperties: int | None = None\n    minProperties: int | None = None\n    required: list[str] | None = None\n    enum: list[Any] | None = None\n    readOnly: bool | None = None'
)

# Add to Header
content = re.sub(
    r'(class Header\(OpenAPIBase\):\n    """OpenAPI Header model\."""\n\n    description: str \| None = None\n    required: bool \| None = None\n    deprecated: bool \| None = None\n    example: Any \| None = None\n    examples: dict\[str, Example \| Reference\] \| None = None)',
    r'\1\n    type: str | None = None\n    format: str | None = None\n    items: SchemaOrReference | list[SchemaOrReference] | None = None\n    collectionFormat: str | None = None\n    default: Any | None = None\n    maximum: float | None = None\n    exclusiveMaximum: bool | None = None\n    minimum: float | None = None\n    exclusiveMinimum: bool | None = None\n    maxLength: int | None = None\n    minLength: int | None = None\n    pattern: str | None = None\n    maxItems: int | None = None\n    minItems: int | None = None\n    uniqueItems: bool | None = None\n    enum: list[Any] | None = None\n    multipleOf: float | None = None',
    content
)

# Add to Parameter
content = re.sub(
    r'(class Parameter\(OpenAPIBase\):[\s\S]*?content: dict\[str, MediaType \| Reference\] \| None = None)',
    r'\1\n    type: str | None = None\n    format: str | None = None\n    collectionFormat: str | None = None\n    default: Any | None = None\n    maximum: float | None = None\n    exclusiveMaximum: bool | None = None\n    minimum: float | None = None\n    exclusiveMinimum: bool | None = None\n    maxLength: int | None = None\n    minLength: int | None = None\n    pattern: str | None = None\n    maxItems: int | None = None\n    minItems: int | None = None\n    uniqueItems: bool | None = None\n    enum: list[Any] | None = None\n    multipleOf: float | None = None\n    items: SchemaOrReference | list[SchemaOrReference] | None = None',
    content
)

# Add to SecurityScheme
content = re.sub(
    r'(class SecurityScheme\(OpenAPIBase\):[\s\S]*?deprecated: bool \| None = None)',
    r'\1\n    flow: str | None = None\n    authorizationUrl: str | None = None\n    tokenUrl: str | None = None\n    scopes: dict[str, str] | None = None',
    content
)

# Add to Operation
content = re.sub(
    r'(class Operation\(OpenAPIBase\):[\s\S]*?servers: list\[Server\] \| None = None)',
    r'\1\n    consumes: list[str] | None = None\n    produces: list[str] | None = None\n    schemes: list[str] | None = None',
    content
)

# Add to OpenAPI
content = re.sub(
    r'(class OpenAPI\(OpenAPIBase\):[\s\S]*?externalDocs: ExternalDocumentation \| None = None)',
    r'\1\n    host: str | None = None\n    basePath: str | None = None\n    schemes: list[str] | None = None\n    consumes: list[str] | None = None\n    produces: list[str] | None = None\n    definitions: dict[str, SchemaOrReference] | None = None\n    parameters: dict[str, Parameter | Reference] | None = None\n    responses: dict[str, Response | Reference] | None = None\n    securityDefinitions: dict[str, SecurityScheme | Reference] | None = None',
    content
)

with open("src/openapi_client/models.py", "w") as f:
    f.write(content)
