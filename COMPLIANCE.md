# OpenAPI 3.2.0 Compliance Report

This document outlines the current level of compliance of `cdd-python-client` with the [OpenAPI 3.2.0 Specification](https://raw.githubusercontent.com/OAI/OpenAPI-Specification/refs/heads/main/versions/3.2.0.md).

## Currently Implemented

- **OpenAPI Object**: `openapi` version parsing (`3.2.0`), `info`, `paths`, `components` (schemas).
- **Info Object**: `title`, `version`.
- **Paths Object**: basic mapping of routes.
- **Path Item Object**: `get`, `post`, `put`, `delete`, `patch`.
- **Operation Object**: `operationId`, `parameters`, `requestBody`, `responses`, `deprecated`, `tags`.
- **Parameter Object**: `name`, `in` (query/path/header/cookie).
- **RequestBody Object**: `content`, `required`.
- **Response Object**: `description`, `content`.
- **Schema Object**: basic types (`string`, `integer`, `boolean`, `array`, `object`, `number`), `properties`, `$ref`.
- **MediaType Object**: `schema` mapping.

## Missing / Partial Implementation (WIP)

- **OpenAPI Object**: `servers`, `security`, `externalDocs`, `webhooks`.
- **Info Object**: `description`, `termsOfService`, `contact`, `license`, `summary`.
- **Server Object** & **Server Variable Object**.
- **Operation Object**: `callbacks`, `security`, `servers`.
- **Responses Object**: advanced status mapping.
- **Header Object**.
- **Security Scheme Object** & **Security Requirement Object**.
- **Components Object**: `responses`, `parameters`, `examples`, `requestBodies`, `headers`, `securitySchemes`, `links`, `callbacks`, `pathItems`.
- **Discriminator Object** & polymorphism (`allOf`, `anyOf`, `oneOf`).
- **XML Object**.

## Goal

Achieve 100% compliance with OpenAPI 3.2.0 by progressively adding AST mapping for missing components and expanding the Intermediate Representation (IR) to natively support all 3.2.0 features.
