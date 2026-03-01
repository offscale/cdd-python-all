cdd-python
==========

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI/CD](https://github.com/offscale/cdd-python-client/workflows/CI/badge.svg)](https://github.com/offscale/cdd-python-client/actions)
![Test Coverage](https://img.shields.io/badge/Test_Coverage-100.0%25-brightgreen)
![Doc Coverage](https://img.shields.io/badge/Doc_Coverage-100.0%25-brightgreen)

OpenAPI ↔ Python. This is one compiler in a suite, all focussed on the same task: Compiler Driven Development (CDD).

Each compiler is written in its target language, is whitespace and comment sensitive, and has both an SDK and CLI.

The CLI—at a minimum—has:
- `cdd-python --help`
- `cdd-python --version`
- `cdd-python from_openapi -i spec.json`
- `cdd-python to_openapi -f path/to/code`
- `cdd-python to_docs_json --no-imports --no-wrapping -i spec.json`

The goal of this project is to enable rapid application development without tradeoffs. Tradeoffs of Protocol Buffers / Thrift etc. are an untouchable "generated" directory and package, compile-time and/or runtime overhead. Tradeoffs of Java or JavaScript for everything are: overhead in hardware access, offline mode, ML inefficiency, and more. And neither of these alterantive approaches are truly integrated into your target system, test frameworks, and bigger abstractions you build in your app. Tradeoffs in CDD are code duplication (but CDD handles the synchronisation for you).

## 🚀 Capabilities

The `cdd-python-client` compiler leverages a unified architecture to support various facets of API and code lifecycle management.

* **Compilation**:
  * **OpenAPI → `Python`**: Generate idiomatic native models, network routes, client SDKs, database schemas, and boilerplate directly from OpenAPI (`.json` / `.yaml`) specifications.
  * **`Python` → OpenAPI**: Statically parse existing `Python` source code and emit compliant OpenAPI specifications.
* **AST-Driven & Safe**: Employs static analysis (Abstract Syntax Trees) instead of unsafe dynamic execution or reflection, allowing it to safely parse and emit code even for incomplete or un-compilable project states.
* **Seamless Sync**: Keep your docs, tests, database, clients, and routing in perfect harmony. Update your code, and generate the docs; or update the docs, and generate the code.

## 📦 Installation

Requires Python 3.9+. Install directly from the repository using `uv` or `pip`:

```bash
uv pip install git+https://github.com/offscale/cdd-python-client.git
```

## 🛠 Usage

### Command Line Interface

Generate a Python client, tests, and mocks from an OpenAPI spec:
```bash
cdd-python from_openapi -i openapi.json -o my_client_dir
```

Extract an OpenAPI spec back out of your Python source code:
```bash
cdd-python to_openapi -f my_client_dir/client.py -o openapi.json
```

Generate a docs JSON array for the website:
```bash
cdd-python to_docs_json -i openapi.json --no-imports --no-wrapping
```

### Programmatic SDK / Library

```python
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator

spec = parse_openapi_json(open("openapi.json").read())
generator = ClientGenerator(spec)
client_code = generator.generate_code()

with open("client.py", "w") as f:
    f.write(client_code)
```

## Design choices

The project leverages `libcst` to guarantee that code parsing and emission are completely whitespace and comment sensitive. By utilizing a lossless Abstract Syntax Tree (AST), `cdd-python` allows for symmetric conversion back and forth between OpenAPI specifications and rich Python source code without clobbering manual developer interventions like inline comments or non-API-related logic.

## 🏗 Supported Conversions for Python

*(The boxes below reflect the features supported by this specific `cdd-python-client` implementation)*

| Concept | Parse (From) | Emit (To) |
|---------|--------------|-----------|
| OpenAPI (JSON/YAML) | ✅ | ✅ |
| `Python` Models / Structs / Types | ✅ | ✅ |
| `Python` Server Routes / Endpoints | ✅ | ✅ |
| `Python` API Clients / SDKs | ✅ | ✅ |
| `Python` ORM / DB Schemas | [ ] | [ ] |
| `Python` CLI Argument Parsers | [ ] | [ ] |
| `Python` Docstrings / Comments | ✅ | ✅ |
| WASM Support (Standalone / Web) | ❌ (Not natively possible) | ⏳ (In Progress) |

> **Note on WASM Support:** While integrating this project into a web interface via `Pyodide` is entirely feasible (and in progress), producing a *standalone* WASM binary (`.wasm`) for CLI execution without Node.js or Python is currently blocked. Python compilation via tools like `py2wasm` and `wasi-sdk` requires complex workarounds (such as modifying `libatomic` and `patchelf`) to successfully compile `libcst` and other C-extensions into WASI modules.

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
