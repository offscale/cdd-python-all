# cdd-python-all

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI/CD](https://github.com/offscale/cdd-python-all/workflows/CI/badge.svg)](https://github.com/offscale/cdd-python-all/actions)
[![Test Coverage](https://img.shields.io/badge/Test_Coverage-100.0%25-brightgreen)](https://github.com/offscale/cdd-python-all/actions)
[![Doc Coverage](https://img.shields.io/badge/Doc_Coverage-100.0%25-brightgreen)](https://github.com/offscale/cdd-python-all/actions)

OpenAPI ↔ Python. This is one compiler in a suite, all focussed on the same task: Compiler Driven Development (CDD).

Each compiler is written in its target language, is whitespace and comment sensitive, and has both an SDK and CLI.

The CLI—at a minimum—has:

- `cdd-python-all --help`
- `cdd-python-all --version`
- `cdd-python-all from_openapi to_sdk_cli -i spec.json`
- `cdd-python-all from_openapi to_sdk -i spec.json`
- `cdd-python-all from_openapi to_server -i spec.json`
- `cdd-python-all to_openapi -f path/to/code`
- `cdd-python-all to_docs_json --no-imports --no-wrapping -i spec.json`
- `cdd-python-all serve_json_rpc --port 8080 --listen 0.0.0.0`

The goal of this project is to enable rapid application development without tradeoffs. Tradeoffs of Protocol Buffers / Thrift etc. are an untouchable "generated" directory and package, compile-time and/or runtime overhead. Tradeoffs of Java or JavaScript for everything are: overhead in hardware access, offline mode, ML inefficiency, and more. And neither of these alternative approaches are truly integrated into your target system, test frameworks, and bigger abstractions you build in your app. Tradeoffs in CDD are code duplication (but CDD handles the synchronisation for you).

## 🚀 Capabilities

The `cdd-python-all` compiler leverages a unified architecture to support various facets of API and code lifecycle management.

- **Compilation**:
    - **OpenAPI → `Python`**: Generate idiomatic native models, network routes, client SDKs, and boilerplate directly from OpenAPI (`.json` / `.yaml`) specifications.
    - **`Python` → OpenAPI**: Statically parse existing `Python` source code and emit compliant OpenAPI specifications.
- **AST-Driven & Safe**: Employs static analysis instead of unsafe dynamic execution or reflection, allowing it to safely parse and emit code even for incomplete or un-compilable project states.
- **Seamless Sync**: Keep your docs, tests, database, clients, and routing in perfect harmony. Update your code, and generate the docs; or update the docs, and generate the code.

## 📦 Installation & Build

### Native Tooling

```bash
python3 -m pip install -e .
python3 -m pytest
```

### Makefile / make.bat

You can also use the included cross-platform Makefiles to fetch dependencies, build, and test:

```bash
# Install dependencies
make deps

# Build the project
make build

# Run tests
make test
```

## 🛠 Usage

### Command Line Interface

```bash
# Generate Python models from an OpenAPI spec
cdd-python-all from_openapi to_sdk -i spec.json -o src/models

# Generate an OpenAPI spec from your Python code
cdd-python-all to_openapi -f src/models -o openapi.json
```

### Programmatic SDK / Library

```py
from cdd import generate_sdk, Config

if __name__ == '__main__':
    config = Config(input_path='spec.json', output_dir='src/models')
    generate_sdk(config)
    print("SDK generation complete.")
```

## 🏗 Supported Conversions for Python

*(The boxes below reflect the features supported by this specific `cdd-python-all` implementation)*

| Features | Parse (From) | Emit (To) |
| --- | --- | --- |
| OpenAPI 3.2.0 | ✅ | ✅ |
| API Client SDK | ✅ | ✅ |
| API Client CLI | [ ] | ✅ |
| Server Routes / Endpoints | ✅ | ✅ |
| ORM / DB Schema | [ ] | [ ] |
| Mocks + Tests | ✅ | ✅ |
| Model Context Protocol (MCP) | [ ] | [ ] |

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
