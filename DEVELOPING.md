# Developing `cdd-python-client`

This project is a compiler converting between OpenAPI 3.2.0 and native Python code using static analysis (`libcst`).

## Getting Started

1. **Install Base Requirements**:
   ```sh
   make install_base
   ```

2. **Install Local Dependencies**:
   ```sh
   make install_deps
   ```

3. **Running Tests**:
   Ensure 100% test coverage!
   ```sh
   make test
   ```

4. **Building Documentation**:
   Ensure 100% doc coverage!
   ```sh
   make build_docs
   ```

## Directory Structure

We use a modular architecture organized by parsing and emitting logic for specific features:

```
src/openapi_client/
├── classes/       # Parsing & emitting class definitions
├── docstrings/    # Parsing & emitting Python docstrings
├── functions/     # Parsing & emitting function signatures
├── mocks/         # Generating mock servers
├── openapi/       # Parsing & emitting OpenAPI JSON
├── routes/        # Parsing & emitting routing configurations
└── tests/         # Generating unit tests
```

Each subdirectory contains:
- `parse.py`: Extracts information from Python AST or OpenAPI dicts to populate the unified Intermediate Representation (IR).
- `emit.py`: Uses the unified IR to generate target code (Python AST) or OpenAPI JSON.
- `__init__.py`

## Updating the AST

Whenever a mock is edited, the changes should mirror into `routes` and `openapi`, ensuring the generated specs are completely synchronized.

## Pre-commit Hooks

We use `pre-commit` to ensure tests and linting run before commits. Install via:

```sh
pre-commit install
```
