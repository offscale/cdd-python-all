# Usage

`cdd-python` provides symmetric conversion back and forth between OpenAPI 3.2.0 specs and Python code.

## Quick Start

1. **Install**:
   ```sh
   pip install git+https://github.com/offscale/cdd-python-client.git
   ```

2. **Generate Client from OpenAPI**:
   ```sh
   cdd-python from_openapi -i spec.json -o src/
   ```

3. **Update OpenAPI from Python Code**:
   ```sh
   cdd-python to_openapi -f src/client.py -o spec.json
   ```

4. **Sync a Project Directory**:
   ```sh
   cdd-python sync --dir src/
   ```

5. **Generate JSON Docs**:
   ```sh
   cdd-python to_docs_json --no-imports --no-wrapping -i spec.json
   ```

## Workflow

1. Write or import an `openapi.json` file.
2. Run `cdd-python from_openapi` to scaffold the `client.py`, `mock_server.py`, and `test_client.py`.
3. You can edit the scaffolded Python directly (adding business logic, editing comments).
4. Run `cdd-python sync --dir src/` to ingest those Python changes back into the OpenAPI specification, maintaining comments and metadata.
