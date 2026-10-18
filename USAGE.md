# Usage

The `cdd-python` CLI can be used in two main modes:

1. **from_openapi**: Generate Python SDK or server mock from OpenAPI JSON.
```bash
cdd-python from_openapi to_sdk -i openapi.json -o my_client
```

2. **to_openapi**: Extract OpenAPI JSON from Python code.
```bash
cdd-python to_openapi -f my_client/client.py -o openapi.json
```

3. **from_arazzo**: Generate Python workflow orchestrators, CLI runners, FastAPI workflow routes, or E2E pytest suites from Arazzo 1.1.0 JSON.
```bash
cdd-python from_arazzo to_sdk -i arazzo.json -o my_workflows
```

4. **to_arazzo**: Extract Arazzo 1.1.0 JSON from Python workflow code (`workflows.py`, `cli_workflows.py`, `routes/workflows.py`, or `test_workflows.py`).
```bash
cdd-python to_arazzo -f my_workflows/src/workflows.py -o arazzo.json
```

It can also sync directories (`--truth arazzo` or `--truth openapi`), generate docs, or serve a JSON-RPC / MCP interface.
