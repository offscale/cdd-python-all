# Usage Guide

The `cdd-python-client` command line interface exposes bidirectional tools to translate OpenAPI into Python, Python into OpenAPI, or continuously synchronize a workspace.

## Command Line Interface (CLI)

The main entry point is the `cdd sync` command.

### 1. Generating Python from OpenAPI
If you have an existing OpenAPI `json` file and want to bootstrap a client, a set of tests, and a FastAPI mock backend:

```bash
cdd sync --from-openapi path/to/openapi.json --to-python path/to/output_dir/
```

**What it does:**
- Parses `openapi.json` into OpenAPI 3.2.0 Pydantic models.
- Emits `client.py` containing Pydantic models and a `Client` class with HTTP methods.
- Emits `mock_server.py` containing a FastAPI app with matching endpoints.
- Emits `test_client.py` containing a Pytest suite for the generated routes.

### 2. Extracting OpenAPI from Python
If you have a Python file with a class structure and you want to generate an OpenAPI specification from it:

```bash
cdd sync --from-python client.py --to-openapi extracted_openapi.json
```

**What it does:**
- Traverses the AST of `client.py`.
- Converts Pydantic/Data classes into JSON Schema (`components.schemas`).
- Converts methods and docstrings into OpenAPI Operations (`paths`).
- Outputs a valid `extracted_openapi.json` file.

### 3. Bidirectional Directory Sync (The CDD Workflow)
This is the most powerful feature. It reconciles an entire directory.

```bash
cdd sync --dir path/to/project/
```

**The Workflow:**
1. You run `cdd sync --dir my_api/`.
2. The tool scans `my_api/client.py`, `my_api/mock_server.py`, and `my_api/test_client.py`.
3. It combines all discovered routes, models, and tests into a unified OpenAPI model.
4. It updates (or creates) `my_api/openapi.json`.
5. It then **regenerates** the missing pieces in the python files.

**Example Scenario:**
- You open `my_api/mock_server.py` and write a new FastAPI route `@app.get("/cats")`.
- You run `cdd sync --dir my_api/`.
- The CLI adds `/cats` to `openapi.json`.
- The CLI adds `def get_cats(self):` to `my_api/client.py`.
- The CLI adds `def test_get_cats():` to `my_api/test_client.py`.

This ensures your documentation, test suite, and implementation can never fall out of sync.
