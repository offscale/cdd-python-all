# WebAssembly (WASM) Support

Compiling a pure Python application to a standalone `.wasm` binary that can run unmodified across different environments (browsers, WASI runtimes) is challenging due to the need for a bundled Python interpreter (like Pyodide or MicroPython) inside the WASM binary.

## Current Status

**Is WASM support possible?** Yes, using Pyodide or similar tools.
**Is it implemented?** Partial. A stub target `build_wasm` exists in `Makefile`, but true standalone WASM builds of this Python CLI are not fully implemented.

To implement this fully in the future, we could compile a custom Pyodide environment using the Emscripten SDK (`emsdk`) found in `../emsdk`, bundle `openapi-python-client` into the virtual filesystem, and output a packaged JS/WASM bundle that exposes the `cdd-python` CLI via a JavaScript wrapper.
