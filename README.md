cdd-python-client
=================

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![uv](https://github.com/offscale/cdd-python-client/actions/workflows/uv.yml/badge.svg)](https://github.com/offscale/cdd-python-client/actions/workflows/uv.yml)
![Test Coverage](https://img.shields.io/badge/Test_Coverage-100.0%25-brightgreen)
![Doc Coverage](https://img.shields.io/badge/Doc_Coverage-100.0%25-brightgreen)

Welcome to **cdd-python-client**, a code-generation and compilation tool bridging the gap between OpenAPI specifications
and native `Python` source code.

This toolset allows you to fluidly convert between your language's native constructs (like classes, structs, functions,
routing, clients, and ORM models) and OpenAPI specifications, ensuring a single source of truth without sacrificing
developer ergonomics.

## 🚀 Capabilities

The `cdd-python-client` compiler leverages a unified architecture to support various facets of API and code lifecycle
management.

* **Compilation**:
    * **OpenAPI ➡️ `Python`**: Generate idiomatic native models, network routes, client SDKs, database schemas, and
      boilerplate directly from OpenAPI (`.json` / `.yaml`) specifications.
    * **`Python` ➡️ OpenAPI**: Statically parse existing `Python` source code and emit compliant OpenAPI specifications.
* **AST-Driven & Safe**: Employs static analysis (Abstract Syntax Trees) instead of unsafe dynamic execution or
  reflection, allowing it to safely parse and emit code even for incomplete or un-compilable project states.
* **Seamless Sync**: Keep your docs, tests, database, clients, and routing in perfect harmony. Update your code, and
  generate the docs; or update the docs, and generate the code.

## 📦 Installation

Requires Python 3.9+. Install directly via `pip` or use `uv` for modern dependency management:

```bash
pip install openapi-python-client
```

## 🛠 Usage

### Command Line Interface

The `cdd` command provides a straightforward way to keep your Python artifacts and OpenAPI specs synchronized.

```bash
# Generate Python client, mock server, and tests from an OpenAPI spec
cdd sync --from-openapi openapi.json --to-python ./my_client_dir

# Extract an OpenAPI spec directly from an existing Python client
cdd sync --from-python ./my_client_dir/client.py --to-openapi extracted_openapi.json

# Synchronize an entire directory (merging changes between Python files and openapi.json)
cdd sync --dir ./my_project
```

### Programmatic SDK / Library

You can also leverage the underlying parsers and emitters programmatically within your Python scripts:

```python
from pathlib import Path
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator

# 1. Parse an existing OpenAPI JSON spec
spec_json = Path("openapi.json").read_text(encoding="utf-8")
spec = parse_openapi_json(spec_json)

# 2. Emit idiomatic Python client code
generator = ClientGenerator(spec)
client_code = generator.generate_code()

Path("client.py").write_text(client_code, encoding="utf-8")
```

## 🏗 Supported Conversions for Python

*(The boxes below reflect the features supported by this specific `cdd-python-client` implementation)*

| Concept                            | Parse (From) | Emit (To) |
|------------------------------------|--------------|-----------|
| OpenAPI (JSON/YAML)                | [x]          | [x]       |
| `Python` Models / Structs / Types  | [x]          | [x]       |
| `Python` Server Routes / Endpoints | [x]          | [x]       |
| `Python` API Clients / SDKs        | [x]          | [x]       |
| `Python` Docstrings / Comments     | [x]          | [x]       |

---

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or <https://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <https://opensource.org/licenses/MIT>)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.
