cdd-python-all
============

[![License](https://img.shields.io/badge/license-Apache--2.0%20OR%20MIT-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![interactive WASM web demo](https://img.shields.io/badge/interactive-WASM_web_demo-blue.svg)](https://offscale.io/wasm_web_demo)
[![CI](https://github.com/offscale/cdd-python-all/actions/workflows/ci.yml/badge.svg)](https://github.com/offscale/cdd-python-all/actions)
[![Test Coverage](https://img.shields.io/badge/test_coverage-100%25-brightgreen.svg)](#)
[![Doc Coverage](https://img.shields.io/badge/doc_coverage-100%25-brightgreen.svg)](#)

**Compiler Driven Development (CDD)** is a development approach designed to eradicate the disconnect between: API specifications; server implementations; client SDKs; and command-line tooling.

Unlike traditional code generators—that treat outputs as disposable or read-only—CDD provides a **complete, standalone compiler** for each supported language. These compilers are fully CST-aware (Concreate Syntax Tree is a whitespace+comment aware Abstract Syntax Tree), allowing true bidirectional synchronization between existing hand-edited source code and OpenAPI specifications.

---

## 🏗️ The Standalone Compiler Architecture

Traditional tools use naïve templating—if you regenerate, your custom code is overwritten.

The CDD ecosystem is fundamentally different. It utilizes language-specific, standalone compilers capable of full AST parsing, semantic diffing, and surgical patching.

**The Core Guarantee:** Every part of the generated codebase is fully editable.
You are encouraged to open the generated routing files, model definitions, and CLI structures, and directly inject your business logic.

- **When your specification changes**, the CDD compiler reads your code, builds an AST, diffs it against the new spec, and safely patches in new endpoints or fields without touching your custom logic.
- **When your codebase changes**, the compiler reverse-engineers your structural updates back into a 100% accurate, authoritative OpenAPI specification.

---

## 🔄 The Bidirectional Synchronization Loop

```mermaid
flowchart TD
    OAS["📄 OpenAPI v3 Spec"] <--> CDD{"⚙️ CDD Compiler"}

    CDD <--> Codebase

    subgraph Codebase ["💻 Application Codebase"]
        direction TB

        subgraph Outputs ["📦 Primary Outputs"]
            direction TB
            CLI["⌨️ CLI Tooling"]
            SDK["📦 Client SDK"]
            Server["🖥️ Server"]

            %% Force vertical stacking inside the subgraph
            CLI ~~~ SDK ~~~ Server
        end

        subgraph Core ["🔗 Core Architecture"]
            direction TB
            Models["🔗 Data Models"]
            Routes["🔀 API Routes"]
            Tests["🧪 Tests"]

            %% Force vertical stacking inside the subgraph
            Models ~~~ Routes ~~~ Tests
        end

        Mocks["🎭 API Mocks / Fakes"]

        %% Simple dependency flow down the page
        Outputs --> Core
        Tests --> Mocks
    end

    style OAS fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px
    style CDD fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px
    style Codebase fill:#fafafa,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray: 5 5
    style Outputs fill:#e8f5e9,stroke:#43a047,stroke-width:2px
    style Core fill:#fff3e0,stroke:#f57c00,stroke-width:2px
```

The CDD lifecycle supports continuous evolution from any starting point:
1. **Generate**: Scaffold servers, SDKs, or CLIs from a central specification.
2. **Edit**: Developers write real, unconstrained code directly in the generated files.
3. **Extract**: Reverse-compile the edited code to produce an updated OpenAPI spec.
4. **Sync**: Apply new specification changes seamlessly into the existing, hand-edited codebase.

---

## 🌐 The Global Language Ecosystem

Every supported language operates on the same core CDD philosophies but is powered by a dedicated, native compiler tailored to that language's specific AST, idioms, and package management.

All implementations share a standardized CLI interface (`cdd [subcommand]`), acting as a universal toolchain.

| Repository | Language | Client; Client CLI; Server | Extra features | Standards | CI Status |
|---|---|---|---|---|---|
| [`cdd-c`](https://github.com/SamuelMarks/cdd-c) | C (C89) | Client; Client CLI; Server | FFI | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-c/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-c/actions/workflows/ci.yml) |
| [`cdd-cpp`](https://github.com/SamuelMarks/cdd-cpp) | C++ | Client; Client CLI; Server | Upgrades Swagger & Google Discovery to OpenAPI 3.2.0 | Google Discovery; Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-cpp/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-cpp/actions/workflows/ci.yml) |
| [`cdd-csharp`](https://github.com/SamuelMarks/cdd-csharp) | C# | Client; Client CLI; Server | CLR | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-csharp/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-csharp/actions/workflows/ci.yml) |
| [`cdd-go`](https://github.com/SamuelMarks/cdd-go) | Go | Client; Client CLI; Server | | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-go/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-go/actions/workflows/ci.yml) |
| [`cdd-java`](https://github.com/SamuelMarks/cdd-java) | Java | Client; Client CLI; Server | | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-java/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-java/actions/workflows/ci.yml) |
| [`cdd-kotlin`](https://github.com/offscale/cdd-kotlin) | Kotlin (ktor for Multiplatform) | Client; Client CLI; Server | Auto-Admin UI | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/offscale/cdd-kotlin/actions/workflows/ci.yml/badge.svg)](https://github.com/offscale/cdd-kotlin/actions/workflows/ci.yml) |
| [`cdd-php`](https://github.com/SamuelMarks/cdd-php) | PHP | Client; Client CLI; Server | | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-php/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-php/actions/workflows/ci.yml) |
| [`cdd-python`](https://github.com/offscale/cdd-python) | Python | N/A (server building blocks) | CLI ↔ SQL ↔ Pydantic ↔ docs ↔ JSON-schema | N/A | [![Linting, testing, coverage, and release](https://github.com/offscale/cdd-python/workflows/Linting,%20testing,%20coverage,%20and%20release/badge.svg)](https://github.com/offscale/cdd-python/actions) |
| [`cdd-python-all`](https://github.com/offscale/cdd-python-all) | Python | Client; Client CLI; Server |  | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/offscale/cdd-python-client/actions/workflows/ci.yml/badge.svg)](https://github.com/offscale/cdd-python-all/actions/workflows/ci.yml) |
| [`cdd-ruby`](https://github.com/SamuelMarks/cdd-ruby) | Ruby | Client; Client CLI; Server |  | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-ruby/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-ruby/actions/workflows/ci.yml) |
| [`cdd-rust`](https://github.com/SamuelMarks/cdd-rust) | Rust | Client; Client CLI; Server |  | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/offscale/cdd-rust/actions/workflows/ci.yml/badge.svg)](https://github.com/offscale/cdd-rust/actions/workflows/ci.yml) |
| [`cdd-sh`](https://github.com/SamuelMarks/cdd-sh) | Shell (/bin/sh) | Client; Client CLI; Server |  | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-sh/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-sh/actions/workflows/ci.yml) |
| [`cdd-swift`](https://github.com/SamuelMarks/cdd-swift) | Swift | Client; Client CLI; Server |  | Swagger 2.0 & OpenAPI 3.2.0 | [![CI](https://github.com/SamuelMarks/cdd-swift/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-swift/actions/workflows/ci.yml) |
| [`cdd-ts`](https://github.com/offscale/cdd-ts) | TypeScript | Client; Client CLI; Server | Auto-Admin UI; Angular; React; Vue; fetch; Axios; Node.js | Swagger 2.0 & OpenAPI 3.2.0 | [![Tests and coverage](https://github.com/offscale/cdd-ts/actions/workflows/ci.yml/badge.svg)](https://github.com/offscale/cdd-ts/actions/workflows/ci.yml) |

---

## 🛠️ Universal CLI Toolchain

A true ecosystem requires standardized tooling. Once a developer learns the CDD toolchain, they can synchronize architecture across the entire polyglot stack.

### Core Subcommands

#### `cdd-python --help`
```text
usage: cdd-python [-h] [--version] {from_openapi,to_openapi,sync,to_docs_json,serve_json_rpc,mcp} ...

Compiler Driven Development (CDD) compiler and transpiler.

positional arguments:
  {from_openapi,to_openapi,sync,to_docs_json,serve_json_rpc,mcp}
    from_openapi        Generate code from an OpenAPI specification.
    to_openapi          Parse the existing codebase and extract an authoritative OpenAPI
                        specification.
    sync                Sync a directory containing client.py, mock_server.py, test_client.py,
                        cli_main.py
    to_docs_json        Convert an OpenAPI specification into a localized, documentation-optimized
                        JSON format.
    serve_json_rpc      Launch a JSON-RPC server for editor and tool integrations.
    mcp                 Run the Model Context Protocol server via stdio.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

#### `cdd-python from_openapi --help`
```text
usage: cdd-python from_openapi [-h] {to_sdk,to_sdk_cli,to_server} ...

positional arguments:
  {to_sdk,to_sdk_cli,to_server}
    to_sdk              Generate a client SDK from an OpenAPI specification.
    to_sdk_cli          Generate a client SDK and a corresponding command-line interface (CLI) from an
                        OpenAPI specification.
    to_server           Generate server boilerplate, models, and routing logic from an OpenAPI
                        specification.

optional arguments:
  -h, --help            show this help message and exit
```

#### `cdd-python from_openapi to_sdk --help`
```text
usage: cdd-python from_openapi to_sdk [-h] [-i INPUT | -d INPUT_DIR] [-o OUTPUT] [--no-github-actions]
                                      [--no-installable-package] [--tests] [--mcp]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, -f INPUT, --input INPUT
                        Path or URL to the OpenAPI specification.
  -d INPUT_DIR, --input-dir INPUT_DIR
                        Directory containing OpenAPI specifications.
  -o OUTPUT, --output OUTPUT
                        Output file or directory path.
  --no-github-actions   Do not generate GitHub Actions scaffolding.
  --no-installable-package
                        Do not generate installable package scaffolding.
  --tests               Generate integration tests and mocks.
  --mcp                 Generate Model Context Protocol (MCP) server and adapter.
```

#### `cdd-python from_openapi to_sdk_cli --help`
```text
usage: cdd-python from_openapi to_sdk_cli [-h] [-i INPUT | -d INPUT_DIR] [-o OUTPUT]
                                          [--no-github-actions] [--no-installable-package] [--tests]
                                          [--mcp]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, -f INPUT, --input INPUT
                        Path or URL to the OpenAPI specification.
  -d INPUT_DIR, --input-dir INPUT_DIR
                        Directory containing OpenAPI specifications.
  -o OUTPUT, --output OUTPUT
                        Output file or directory path.
  --no-github-actions   Do not generate GitHub Actions scaffolding.
  --no-installable-package
                        Do not generate installable package scaffolding.
  --tests               Generate integration tests and mocks.
  --mcp                 Generate Model Context Protocol (MCP) server and adapter.
```

#### `cdd-python from_openapi to_server --help`
```text
usage: cdd-python from_openapi to_server [-h] [-i INPUT | -d INPUT_DIR] [-o OUTPUT]
                                         [--no-github-actions] [--no-installable-package] [--tests]
                                         [--mcp]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, -f INPUT, --input INPUT
                        Path or URL to the OpenAPI specification.
  -d INPUT_DIR, --input-dir INPUT_DIR
                        Directory containing OpenAPI specifications.
  -o OUTPUT, --output OUTPUT
                        Output file or directory path.
  --no-github-actions   Do not generate GitHub Actions scaffolding.
  --no-installable-package
                        Do not generate installable package scaffolding.
  --tests               Generate integration tests and mocks.
  --mcp                 Generate Model Context Protocol (MCP) server and adapter.
```

#### `cdd-python to_openapi --help`
```text
usage: cdd-python to_openapi [-h] -i INPUT [-o OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, -f INPUT, --input INPUT
                        Path to source code directory or file
  -o OUTPUT, --output OUTPUT
                        Output file or directory path
```

#### `cdd-python sync --help`
```text
usage: cdd-python sync [-h] -i INPUT [-t {class,sqlalchemy,function,openapi}]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, -d INPUT, --input INPUT
                        Path to directory containing Python files to sync
  -t {class,sqlalchemy,function,openapi}, --truth {class,sqlalchemy,function,openapi}
                        Designate a single source of truth for synchronization.
```

#### `cdd-python to_docs_json --help`
```text
usage: cdd-python to_docs_json [-h] -i INPUT [--no-imports] [--no-wrapping] [-o OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, -f INPUT, --input INPUT
                        Path or URL to the OpenAPI specification.
  --no-imports          Omit the imports field.
  --no-wrapping         Omit the wrapper fields.
  -o OUTPUT, --output OUTPUT
                        Output file or directory path.
```

#### `cdd-python serve_json_rpc --help`
```text
usage: cdd-python serve_json_rpc [-h] [-p PORT] [-l LISTEN]

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Port to listen on
  -l LISTEN, --listen LISTEN
                        Address to listen on
```

#### `cdd-python mcp --help`
```text
usage: cdd-python mcp [-h]

optional arguments:
  -h, --help  show this help message and exit
```

### Detail Features Beyond Common Subset

- **Model Context Protocol (MCP)**: Native support to generate an MCP server and adapter (`--mcp`), and run the MCP server over stdio.
- **Directory Synchronization**: Uniquely features a `sync` command to harmonize `client.py`, `mock_server.py`, `test_client.py`, and `cli_main.py` with configurable sources of truth (`class`, `sqlalchemy`, `function`, `openapi`).
- **Comprehensive Scaffolding**: Optionally generates GitHub Actions pipelines and installable Python package scaffolding automatically.
- **Integration Testing & Mocks**: Emits full integration tests and mock servers during generation (`--tests`).
- **Batch Processing**: Capable of reading from an entire directory of OpenAPI specifications (`--input-dir`) simultaneously.

---

## 🚀 The End of "Spec Drift"

With Compiler Driven Development, specifications and code are no longer loosely coupled artifacts. They are strict, isomorphic reflections of one another, maintained by dedicated standalone compilers.

Choose your language ecosystem above and start treating your architecture as a seamlessly compiled, endlessly editable whole.

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
