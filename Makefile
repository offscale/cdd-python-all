.PHONY: install_base install_deps build_docs build test run help all build_wasm

# Default target
.DEFAULT_GOAL := help

install_base:
	@echo "Installing base dependencies..."
	uv python install
	uv pip install --upgrade pip build hatchling
	uv pip install -e ".[dev]"
install_deps:
	@echo "Installing local dependencies..."
	uv pip install -e ".[dev]"

build_docs:
	@echo "Building docs..."
	@mkdir -p $(if $(word 2, $(MAKECMDGOALS)),$(word 2, $(MAKECMDGOALS)),docs)
	uv run python -m pydoc -w src/openapi_client/cli.py
	@mv cli.html $(if $(word 2, $(MAKECMDGOALS)),$(word 2, $(MAKECMDGOALS)),docs)/

build:
	@echo "Building CLI binary (wheel)..."
	uv run python -m build --wheel --outdir $(if $(word 2, $(MAKECMDGOALS)),$(word 2, $(MAKECMDGOALS)),dist)
	@echo "Build complete."

build_wasm:
	@echo "Building WASM..."
	@echo "WASM build using Emscripten. See WASM.md."

test:
	@echo "Running tests..."
	uv run pytest tests/ --cov=src/openapi_client --cov-report=term-missing

run: build
	@echo "Running CLI..."
	uv run cdd-python $(filter-out $@,$(MAKECMDGOALS))

help:
	@echo "Available commands:"
	@echo "  install_base : install language runtime and anything else relevant"
	@echo "  install_deps : install local dependencies"
	@echo "  build_docs   : build the API docs and put them in the 'docs' directory"
	@echo "  build        : build the CLI binary"
	@echo "  build_wasm   : build the WASM binary"
	@echo "  test         : run tests locally"
	@echo "  run          : run the CLI"
	@echo "  help         : show what options are available"
	@echo "  all          : show help text"

all: help

%:
	@:
