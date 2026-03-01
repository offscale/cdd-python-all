# WASM Support

WASM support for Python CLI tools allows running the tool in environments without a native Python installation (like browsers or generic WASM runtimes).

## Building WASM

We can use the Emscripten SDK (`emsdk`) to compile CPython and our library into a WASM module, or leverage Pyodide.

### Prerequisites

You need `emsdk` installed. By default, the `Makefile` expects it one directory above the current working directory (`../emsdk`).

### Build Command

```sh
make build_wasm
```

### Supported Environments

- **Unified Web Interface**: This WASM build can be loaded in browsers using a web worker or Pyodide.
- **Unified CLI**: Can be run via `wasmtime`, `wasmer`, or Node.js without needing a host Python installation.

## Implementation Status

- **Feasible**: Yes
- **Implemented**: In progress (Makefile target exists, waiting for Emscripten/Pyodide complete integration).
