cdd-python-all
==============

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI/CD](https://github.com/offscale/cdd-python-all/workflows/CI/badge.svg)](https://github.com/offscale/cdd-python-all/actions)
[![Test Coverage](https://img.shields.io/badge/Test_Coverage-100.0%25-brightgreen)](https://github.com/offscale/cdd-python-all/actions)
[![Doc Coverage](https://img.shields.io/badge/Doc_Coverage-100.0%25-brightgreen)](https://github.com/offscale/cdd-python-all/actions)

OpenAPI ↔ Python. This is one compiler in a suite, all focussed on the same task: Compiler Driven Development (CDD).

Each compiler is written in its target language, is whitespace and comment sensitive, and has both an SDK and CLI.

The CLI—at a minimum—has:
- `python3 -m cdd_python_all --help`
- `python3 -m cdd_python_all --version`
- `python3 -m cdd_python_all from_openapi -i spec.json`
- `python3 -m cdd_python_all to_openapi -f path/to/code`
- `python3 -m cdd_python_all to_docs_json --no-imports --no-wrapping -i spec.json`

The goal of this project is to enable rapid application development without tradeoffs. Tradeoffs of Protocol Buffers / Thrift etc. are an untouchable "generated" directory and package, compile-time and/or runtime overhead. Tradeoffs of Java or JavaScript for everything are: overhead in hardware access, offline mode, ML inefficiency, and more. And neither of these alterantive approaches are truly integrated into your target system, test frameworks, and bigger abstractions you build in your app. Tradeoffs in CDD are code duplication (but CDD handles the synchronisation for you).

## 🚀 Capabilities

The `cdd-python-all` compiler leverages a unified architecture to support various facets of API and code lifecycle management.

* **Compilation**:
  * **OpenAPI → `Python`**: Generate idiomatic native models, network routes, client SDKs, database schemas, and boilerplate directly from OpenAPI (`.json` / `.yaml`) specifications.
  * **`Python` → OpenAPI**: Statically parse existing `Python` source code and emit compliant OpenAPI specifications.
* **AST-Driven & Safe**: Employs static analysis (Abstract Syntax Trees) instead of unsafe dynamic execution or reflection, allowing it to safely parse and emit code even for incomplete or un-compilable project states.
* **Seamless Sync**: Keep your docs, tests, database, clients, and routing in perfect harmony. Update your code, and generate the docs; or update the docs, and generate the code.

## 📦 Installation

Requires Python 3.9+. Run `pip install cdd-python-all`

## 🛠 Usage

### Command Line Interface


```bash
# Generate a Python SDK and an interactive CLI from an OpenAPI spec
python3 -m cdd_python_all from_openapi to_sdk_cli -i ./openapi.json -o ./my_generated_client

# Extract an OpenAPI spec from your modified Python client code
python3 -m cdd_python_all to_openapi -f ./my_generated_client/client.py -o ./updated_openapi.json

# Extract documentation JSON from your OpenAPI spec
python3 -m cdd_python_all to_docs_json --no-imports --no-wrapping -i ./openapi.json -o docs.json
```


### Programmatic SDK / Library


```python
import libcst as cst
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator

# Load and parse an OpenAPI specification
with open("openapi.json", "r") as f:
    spec = parse_openapi_json(f.read())

# Generate a Client SDK
generator = ClientGenerator(spec)
client_code = generator.generate_code()

# Write the generated code to a file
with open("client.py", "w") as f:
    f.write(client_code)
```


## Design choices

We use `libcst` to safely parse and generate Python ASTs. This allows us to modify source code accurately while retaining comments and whitespace.

## 🏗 Supported Conversions for Python

*(The boxes below reflect the features supported by this specific `cdd-python-all` implementation)*


| Concept | Parse (From) | Emit (To) |
|---------|--------------|-----------|
| OpenAPI (JSON/YAML) | [x] | [x] |
| `Python` Models / Structs / Types | [x] | [x] |
| `Python` Server Routes / Endpoints | [x] | [x] |
| `Python` API Clients / SDKs | [x] | [x] |
| `Python` ORM / DB Schemas | [ ] | [ ] |
| `Python` CLI Argument Parsers | [x] | [x] |
| `Python` Docstrings / Comments | [x] | [x] |




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
