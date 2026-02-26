# CDD Python Client (OpenAPI 3.2.0)

[![uv](https://github.com/offscale/cdd-python-client/actions/workflows/uv.yml/badge.svg)](https://github.com/offscale/cdd-python-client/actions/workflows/uv.yml)

A highly modular, strictly typed, bidirectional OpenAPI 3.2.0 client generator and extractor for Python. 

Unlike traditional "one-way" code generators, this library treats both **Python Code** (Clients, FastAPI Mocks, Pytest suites) and **JSON Specifications** as equal sources of truth. You can edit a mock server, and the CLI will automatically update your OpenAPI spec, your client SDK, and your tests.

## Features
- **Contract-Driven Development**: Multi-directional synchronization between API specifications and code.
- **OpenAPI 3.2.0 Support**: Fully typed models compliant with the latest spec.
- **Preserves Formatting**: Uses `libcst` (Abstract Syntax Trees) instead of regex/templating, meaning it parses and injects code cleanly without ruining your manual modifications.
- **100% Test Coverage & Type Safety**: Guaranteed stability through rigorous CI/CD standards.

## Quickstart

### Installation

```bash
pip install cdd-python-client
```

*(Note: Currently requires building from source or installing via PyPI once published).*

### Usage Example

**1. Generate a client from an OpenAPI spec:**
```bash
cdd sync --from-openapi openapi.json --to-python ./my_client_sdk
```
This generates `client.py`, `mock_server.py`, and `test_client.py` inside `./my_client_sdk`.

**2. The CDD Workflow (Sync Directory):**
Edit `./my_client_sdk/mock_server.py` to add a new route:
```python
@app.post("/users")
def create_user():
    """Create a new user in the system."""
    pass
```

Now, sync the directory:
```bash
cdd sync --dir ./my_client_sdk
```

The CLI will:
1. Parse your new mock using AST.
2. Update `openapi.json` to include the `POST /users` path.
3. Inject the `create_user` method into `client.py`.
4. Create a `test_create_user` stub in `test_client.py`.

For more details, see [USAGE.md](USAGE.md).
