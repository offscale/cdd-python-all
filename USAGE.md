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

It can also sync directories, generate docs, or serve a JSON-RPC interface.
