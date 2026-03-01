@echo off
setlocal enabledelayedexpansion

set TASK=%1
if "%TASK%"=="" set TASK=help

if "%TASK%"=="install_base" goto install_base
if "%TASK%"=="install_deps" goto install_deps
if "%TASK%"=="build_docs" goto build_docs
if "%TASK%"=="build" goto build
if "%TASK%"=="test" goto test
if "%TASK%"=="run" goto run
if "%TASK%"=="build_wasm" goto build_wasm
if "%TASK%"=="build_docker" goto build_docker
if "%TASK%"=="run_docker" goto run_docker
if "%TASK%"=="help" goto help
if "%TASK%"=="all" goto help

:help
echo Available tasks:
echo   install_base : install language runtime (Python 3 via winget)
echo   install_deps : install local dependencies
echo   build_docs   : build the API docs [dir]
echo   build        : build the CLI [dir]
echo   test         : run tests locally
echo   run          : run the CLI [args...]
echo   build_wasm   : build WASM output
echo   build_docker : build Docker images
echo   run_docker   : run and test Docker containers
echo   help         : show this help text
echo   all          : show this help text
goto :EOF

:install_base
echo Installing base tools (Python 3)
winget install Python.Python.3.11
goto :EOF

:install_deps
pip install uv
uv venv
uv pip install -e ".[dev]"
goto :EOF

:build_docs
set DOCS_DIR=%2
if "%DOCS_DIR%"=="" set DOCS_DIR=docs
echo Building docs in %DOCS_DIR%
mkdir "%DOCS_DIR%" 2>NUL
.venv\Scripts\python.exe -m pdoc src/openapi_client -o "%DOCS_DIR%"
goto :EOF

:build
set BIN_DIR=%2
if "%BIN_DIR%"=="" set BIN_DIR=dist
echo Building binary/package in %BIN_DIR%
mkdir "%BIN_DIR%" 2>NUL
.venv\Scripts\python.exe -m build --wheel --outdir "%BIN_DIR%"
goto :EOF

:build_wasm
echo Building WASM to dist\wasm
mkdir dist\wasm 2>NUL
echo A full CPython WASM standalone build requires Pyodide. Stubbed for now. > dist\wasm\README.txt
goto :EOF

:test
.venv\Scripts\python.exe -m pytest tests/
goto :EOF

:run
call :build
set RUN_ARGS=
:loop
shift
if "%1"=="" goto after_loop
set RUN_ARGS=%RUN_ARGS% %1
goto loop
:after_loop
.venv\Scripts\python.exe -m openapi_client.cli %RUN_ARGS%
goto :EOF

:build_docker
echo Building Docker images
docker build -t cdd-python-client-alpine -f alpine.Dockerfile .
docker build -t cdd-python-client-debian -f debian.Dockerfile .
goto :EOF

:run_docker
call :build_docker
docker run -d -p 8080:8080 --name cdd_alpine cdd-python-client-alpine
timeout /t 3
curl -X POST http://localhost:8080 -H "Content-Type: application/json" -d "{"jsonrpc": "2.0", "method": "missing", "id": 1}"
docker stop cdd_alpine
docker rm cdd_alpine
docker run -d -p 8080:8080 --name cdd_debian cdd-python-client-debian
timeout /t 3
curl -X POST http://localhost:8080 -H "Content-Type: application/json" -d "{"jsonrpc": "2.0", "method": "missing", "id": 1}"
docker stop cdd_debian
docker rm cdd_debian
goto :EOF
