# OpenAPI 3.2.0 Compliance

This project is actively pursuing 100% compliance with the **OpenAPI 3.2.0 Specification**.

## Supported Features

The following OpenAPI 3.2.0 structures are fully modeled in `src/openapi_client/models.py` via Pydantic and actively supported in the AST parsing/emitting pipeline:

### Document Structure
- **OpenAPI Object**: Core root object supporting `openapi: 3.2.0`, `info`, `paths`, `components`, `servers`, `security`, `tags`, `webhooks`, and `$self`.
- **Info Object**: Fully supported, including `Contact` and `License` objects.
- **Server / ServerVariable Objects**: Fully modeled.
- **Paths / PathItem Objects**: Supports standard HTTP methods (`get`, `post`, `put`, `delete`, `patch`, `options`, `head`, `trace`) as well as the new OAS 3.2.0 `query` method and `additionalOperations` mapping.
- **Operation Object**: Supports `operationId`, `summary`, `description`, `parameters`, `requestBody`, `responses`, `callbacks`, `security`, etc.
- **Components Object**: Models schemas, responses, parameters, examples, requestBodies, headers, securitySchemes, links, callbacks, pathItems, and `mediaTypes` (new in OAS 3.2.0).

### Schema & Data Types
- **Schema Object**: Includes full JSON Schema validation properties (`type`, `properties`, `items`, `allOf`, `anyOf`, `oneOf`, `discriminator`, etc.). 
- **Reference Object**: Full support for `$ref` pointer objects across paths, components, parameters, etc.

### Media Types & Encodings (OAS 3.2.0 Enhancements)
- **MediaType Object**: Supports the newly defined streaming and sequential payload fields `itemSchema`, `prefixEncoding`, and `itemEncoding`.
- **Encoding Object**: Supports headers, standard encodings, `prefixEncoding`, and `itemEncoding`.

## Partial / Ongoing Support
While the data models strictly validate against OpenAPI 3.2.0 schemas, the *AST manipulation* logic is still incrementally supporting features:

1. **Complex Parameters**: Deep object serializations for Query strings (`spaceDelimited`, `pipeDelimited`) are modeled but code-generation for them currently maps to generic `Any` types in the Python client.
2. **Streaming / Webhooks**: Models exist, but FastAPI mock extraction and test extraction for event-driven / server-sent events (`text/event-stream`) is currently stubbed.
3. **Implicit Connections**: Cross-document `$ref` resolution is currently limited to local `#/...` JSON pointers within the `openapi.json` file.

## Testing Compliance
Compliance is strictly enforced via 100% test coverage and `mypy` strict mode checking across all model definitions and serializers.
