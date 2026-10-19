# Usage

The `cdd-python-all` (also installed as `cdd-python`) CLI and `openapi_client` Python SDK provide lossless, bidirectional compilation between OpenAPI 3.2.0 / Swagger 2.0 / Arazzo 1.1.0 specifications and Python source code.

## CLI Modes

1. **`from_openapi`**: Generate a Python Client SDK (`to_sdk`), Client CLI (`to_sdk_cli`), or FastAPI + SQLAlchemy Server (`to_server`) from an OpenAPI JSON file (`-i`) or directory (`-d`).
```bash
cdd-python-all from_openapi to_sdk -i openapi.json -o my_client --tests
cdd-python-all from_openapi to_sdk_cli -i openapi.json -o my_cli --tests --mcp
cdd-python-all from_openapi to_server -i openapi.json -o my_server --tests --arazzo arazzo.json
```

2. **`to_openapi`**: Statically extract an OpenAPI 3.2.0 JSON specification from a Python file or project directory.
```bash
cdd-python-all to_openapi -i my_client -o openapi.json
```

3. **`from_arazzo`**: Generate Python workflow orchestrators (`to_sdk`), CLI workflow runners (`to_sdk_cli`), FastAPI workflow routes (`to_server`), or standalone E2E pytest suites (`to_tests`) from an Arazzo 1.1.0 JSON specification.
```bash
cdd-python-all from_arazzo to_sdk -i arazzo.json -o my_workflows --tests
cdd-python-all from_arazzo to_sdk_cli -i arazzo.json -o my_workflows_cli --tests
cdd-python-all from_arazzo to_server -i arazzo.json -o my_server --tests
cdd-python-all from_arazzo to_tests -i arazzo.json -o my_workflows
```

4. **`to_arazzo`**: Extract an Arazzo 1.1.0 JSON specification from Python workflow code (`workflows.py`, `cli_workflows.py`, `routes/workflows.py`, or `test_workflows.py`) or a project directory.
```bash
cdd-python-all to_arazzo -i my_workflows/src/workflows.py -o arazzo.json
```

5. **`sync`**: Synchronize a directory containing `client.py`, `models.py`, `mock_server.py`, `test_client.py`, `cli_main.py`, `workflows.py`, `openapi.json`, and `arazzo.json` with a configurable source of truth (`class`, `sqlalchemy`, `function`, `openapi`, `arazzo`, or `workflow`).
```bash
cdd-python-all sync -i my_client --truth openapi
```

6. **`to_docs_json`**: Generate documentation-ready Python code snippets JSON from an OpenAPI or Arazzo specification.
```bash
cdd-python-all to_docs_json --no-imports --no-wrapping -i openapi.json -o docs.json
```

7. **`serve_json_rpc` & `mcp`**: Expose the compiler over a JSON-RPC 2.0 HTTP server or a Model Context Protocol (`stdio`) server.
```bash
cdd-python-all serve_json_rpc --port 8080 --listen 127.0.0.1
cdd-python-all mcp
```
