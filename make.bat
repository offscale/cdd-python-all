@echo off
setlocal enabledelayedexpansion

if "%~1"=="" goto help
if "%~1"=="install_base" goto install_base
if "%~1"=="install_deps" goto install_deps
if "%~1"=="build_docs" goto build_docs
if "%~1"=="build" goto build
if "%~1"=="build_wasm" goto build_wasm
if "%~1"=="test" goto test
if "%~1"=="run" goto run
if "%~1"=="help" goto help
if "%~1"=="all" goto help

echo Unknown command: "%~1"
goto help

:install_base
echo Installing base dependencies...
uv python install
uv pip install --upgrade pip build hatchling
uv pip install -e .[dev]
goto :eof

:install_deps
echo Installing local dependencies...
uv pip install -e .[dev]
goto :eof

:build_docs
echo Building docs...
set DOCS_DIR=docs
if not "%~2"=="" set DOCS_DIR=%~2
if not exist %DOCS_DIR% mkdir %DOCS_DIR%
uv run python -m pydoc -w src/openapi_client/cli.py
move cli.html %DOCS_DIR%\
goto :eof

:build
echo Building CLI binary (wheel)...
set OUT_DIR=dist
if not "%~2"=="" set OUT_DIR=%~2
uv run python -m build --wheel --outdir %OUT_DIR%
echo Build complete.
goto :eof

:build_wasm
echo Building WASM...
echo WASM build using Pyodide/Emscripten is supported in theory. See WASM.md.
goto :eof

:test
echo Running tests...
uv run pytest tests/ --cov=src/openapi_client --cov-report=term-missing
goto :eof

:run
call :build
echo Running CLI...
shift
set "args="
:run_loop
if "%~1"=="" goto run_exec
set "args=%args% %1"
shift
goto run_loop
:run_exec
uv run cdd-python %args%
goto :eof

:help
echo Available commands:
echo   install_base : install language runtime and anything else relevant
echo   install_deps : install local dependencies
echo   build_docs   : build the API docs and put them in the "docs" directory
echo   build        : build the CLI binary
echo   build_wasm   : build the WASM binary
echo   test         : run tests locally
echo   run          : run the CLI
echo   help         : show what options are available
echo   all          : show help text
goto :eof
