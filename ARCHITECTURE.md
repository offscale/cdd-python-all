# Architecture

The `cdd-python-client` is designed around a strictly modular, bidirectional Code-to-Spec and Spec-to-Code architecture, heavily utilizing Abstract Syntax Trees (AST).

## Core Concepts

1. **Contract-Driven Development (CDD)**: The source of truth can be dynamically negotiated. You can start with an OpenAPI specification (`openapi.json`) or you can start with Python code (FastAPI mocks, Pydantic models, or pytest tests).
2. **Abstract Syntax Trees (AST)**: Instead of regex or simple templating, this tool utilizes `libcst` (Concrete Syntax Tree) to read and write Python code. This preserves comments, whitespace, and structural integrity.
3. **Pydantic Models**: The OpenAPI 3.2.0 specification is modeled heavily using Pydantic (`models.py`). This guarantees in-memory type safety and validation when parsing or emitting specifications.

## Directory Structure

The repository is modularized by domain, ensuring that parsing and emitting logic for specific Python/OpenAPI concepts remain isolated:

```
src/openapi_client/
├── models.py                   # Single Source of Truth for OpenAPI 3.2.0 specs
├── cli.py                      # CLI entrypoints and unified sync workflows
├── openapi/                    # JSON/Dict Serialization
│   ├── parse.py
│   └── emit.py
├── classes/                    # Pydantic Models <-> OpenAPI Components/Schemas
│   ├── parse.py                # Extracts JSON schemas from Python classes
│   └── emit.py                 # Emits Pydantic models from JSON schemas
├── functions/                  # Python Methods <-> OpenAPI Operations
│   ├── parse.py
│   └── emit.py
├── docstrings/                 # Python Docstrings <-> OpenAPI Summary/Description
│   ├── parse.py
│   └── emit.py
├── routes/                     # Client generation (combining classes + functions)
│   ├── parse.py
│   └── emit.py
├── mocks/                      # FastAPI Mocks <-> OpenAPI Paths/Operations
│   ├── parse.py
│   └── emit.py
└── tests/                      # Pytest functions <-> OpenAPI Examples/Validation
    ├── parse.py
    └── emit.py
```

## The Sync Lifecycle (`cdd sync --dir`)

When using the unified sync workflow, the system performs a bidirectional merge:
1. **Parse**: `libcst` Visitors traverse `client.py`, `mock_server.py`, and `test_client.py`. Any discovered routes, Pydantic models, and docstrings are extracted and merged into the in-memory OpenAPI Pydantic model.
2. **Merge**: If an `openapi.json` exists, it is parsed and used as the baseline. Code-extracted definitions overlay or expand the JSON definitions.
3. **Emit**: The fully reconciled OpenAPI model is serialized back to `openapi.json`. Then, `libcst` generators rebuild `client.py`, `mock_server.py`, and `test_client.py`, ensuring 100% synchronization across the client, backend mocks, tests, and documentation.
