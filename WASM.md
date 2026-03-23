# WebAssembly (WASM) Support

Compiling a pure Python application to a standalone `.wasm` binary that can run unmodified across different environments (browsers, WASI runtimes) is challenging due to the need for a bundled Python interpreter (like Pyodide or MicroPython) inside the WASM binary.

## Current Status

**Is WASM support possible?** Yes, using `py2wasm`.
**Is it implemented?** Yes. A `build_wasm` target exists in `Makefile` which compiles the CLI to a standalone `.wasm` binary.

To build it manually:
```bash
pip install py2wasm
make build_wasm
```
This produces `bin/cdd-python-all.wasm`.
