cdd-Python
============

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI/CD](https://github.com/offscale/cdd-python-client/workflows/CI/badge.svg)](https://github.com/offscale/cdd-python-client/actions)
![Test Coverage](https://img.shields.io/badge/Test_Coverage-100.0%25-brightgreen)
![Doc Coverage](https://img.shields.io/badge/Doc_Coverage-100.0%25-brightgreen)

OpenAPI ↔ Python. This is one compiler in a suite, all focussed on the same task: Compiler Driven Development (CDD).

Each compiler is written in its target language, is whitespace and comment sensitive, and has both an SDK and CLI.

The CLI—at a minimum—has:
- `cdd --help`
- `cdd --version`
- `cdd sync --from-openapi spec.json --to-python out_dir`
- `cdd sync --from-python client.py --to-openapi spec.json`
- `cdd to_docs_json --no-imports --no-wrapping -i spec.json`

The goal of this project is to enable rapid application development without tradeoffs. Tradeoffs of Protocol Buffers / Thrift etc. are an untouchable "generated" directory and package, compile-time and/or runtime overhead. Tradeoffs of Java or JavaScript for everything are: overhead in hardware access, offline mode, ML inefficiency, and more. And neither of these alterantive approaches are truly integrated into your target system, test frameworks, and bigger abstractions you build in your app. Tradeoffs in CDD are code duplication (but CDD handles the synchronisation for you).

## 🚀 Capabilities

The `cdd-python-client` compiler leverages a unified architecture to support various facets of API and code lifecycle management.

* **Compilation**:
  * **OpenAPI → `Python`**: Generate idiomatic native models, network routes, client SDKs, database schemas, and boilerplate directly from OpenAPI (`.json` / `.yaml`) specifications.
  * **`Python` → OpenAPI**: Statically parse existing `Python` source code and emit compliant OpenAPI specifications.
* **AST-Driven & Safe**: Employs static analysis (Abstract Syntax Trees) instead of unsafe dynamic execution or reflection, allowing it to safely parse and emit code even for incomplete or un-compilable project states.
* **Seamless Sync**: Keep your docs, tests, database, clients, and routing in perfect harmony. Update your code, and generate the docs; or update the docs, and generate the code.

## 📦 Installation

Requires Python 3.9+.

```bash
pip install openapi-python-client
```

## 🛠 Usage

### Command Line Interface

Generate a Python client from an OpenAPI specification:
```bash
cdd sync --from-openapi spec.json --to-python ./my_client
```

Extract an OpenAPI specification from an existing Python client module:
```bash
cdd sync --from-python ./my_client/client.py --to-openapi spec.json
```

Generate a docs JSON:
```bash
cdd to_docs_json -i spec.json --no-imports
```

### Programmatic SDK / Library

```python
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator

spec = parse_openapi_json(open('spec.json').read())
generator = ClientGenerator(spec)
print(generator.generate_code())
```

## Design choices

The `cdd-python-client` leverages LibCST for parsing and generating Python Abstract Syntax Trees (AST). LibCST is chosen over Python's built-in `ast` module because it preserves whitespace, comments, and structure, which is crucial for a bidirectional compiler that doesn't mess up your code formatting when syncing changes. Pydantic is used for models generation to provide idiomatic and robust validation for the client interfaces.

## 🏗 Supported Conversions for Python

*(The boxes below reflect the features supported by this specific `cdd-python-client` implementation)*

| Concept | Parse (From) | Emit (To) |
|---------|--------------|-----------|
| OpenAPI (JSON/YAML) | [✅] | [✅] |
| `Python` Models / Structs / Types | [✅] | [✅] |
| `Python` Server Routes / Endpoints | [✅] | [✅] |
| `Python` API Clients / SDKs | [✅] | [✅] |
| `Python` ORM / DB Schemas | [ ] | [ ] |
| `Python` CLI Argument Parsers | [ ] | [ ] |
| `Python` Docstrings / Comments | [✅] | [✅] |

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