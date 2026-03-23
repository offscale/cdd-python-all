.PHONY: install_base install_deps build_docs build test run help all build_wasm build_docker run_docker

.DEFAULT_GOAL := help

# Extract arguments for build, build_docs, run
ifeq ($(firstword $(MAKECMDGOALS)),build)
  BIN_DIR := $(word 2,$(MAKECMDGOALS))
  ifeq ($(BIN_DIR),)
    BIN_DIR := dist
  else
    $(eval $(BIN_DIR):;@:)
  endif
endif

ifeq ($(firstword $(MAKECMDGOALS)),build_docs)
  DOCS_DIR := $(word 2,$(MAKECMDGOALS))
  ifeq ($(DOCS_DIR),)
    DOCS_DIR := docs
  else
    $(eval $(DOCS_DIR):;@:)
  endif
endif

ifeq ($(firstword $(MAKECMDGOALS)),run)
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif

install_base:
	@echo "Installing base tools (Python 3)"
	@if [ -x "$$(command -v apt-get)" ]; then sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv; fi
	@if [ -x "$$(command -v brew)" ]; then brew install python; fi
	@if [ -x "$$(command -v dnf)" ]; then sudo dnf install -y python3 python3-pip; fi

install_deps:
	pip install uv || pip3 install uv
	uv venv || python3 -m venv .venv
	uv pip install -e ".[dev]" || pip install -e ".[dev]"

build_docs:
	@echo "Building docs in $(DOCS_DIR)"
	@mkdir -p $(DOCS_DIR)
	.venv/bin/python3 -m pdoc src/openapi_client -o $(DOCS_DIR) || pdoc src/openapi_client -o $(DOCS_DIR)

build:
	@echo "Building binary/package in $(BIN_DIR)"
	@mkdir -p $(BIN_DIR)
	uv build --wheel --out-dir $(BIN_DIR)

build_wasm:
	@echo "Building WASM to bin/"
	@mkdir -p bin
	if [ -d .venv ]; then .venv/bin/python3 -m py2wasm src/openapi_client/cli.py -o bin/cdd-python-all.wasm; else py2wasm src/openapi_client/cli.py -o bin/cdd-python-all.wasm; fi

test:
	.venv/bin/python3 -m pytest tests/ || pytest tests/

run: build
	.venv/bin/python3 -m openapi_client.cli $(RUN_ARGS) || cdd-python $(RUN_ARGS)

help:
	@echo "Available tasks:"
	@echo "  install_base : install language runtime (Python 3)"
	@echo "  install_deps : install local dependencies"
	@echo "  build_docs   : build the API docs [dir]"
	@echo "  build        : build the CLI [dir]"
	@echo "  test         : run tests locally"
	@echo "  run          : run the CLI [args...]"
	@echo "  build_wasm   : build WASM output"
	@echo "  build_docker : build Docker images"
	@echo "  run_docker   : run and test Docker containers"
	@echo "  help         : show this help text"
	@echo "  all          : show this help text"

all: help

build_docker:
	@echo "Building Docker images"
	docker build -t cdd-python-all-alpine -f alpine.Dockerfile .
	docker build -t cdd-python-all-debian -f debian.Dockerfile .

run_docker: build_docker
	docker run -d -p 8080:8080 --name cdd_alpine cdd-python-all-alpine
	sleep 3
	curl -X POST http://localhost:8080 -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "method": "missing", "id": 1}' || echo "container failed to respond"
	docker stop cdd_alpine
	docker rm cdd_alpine
	docker run -d -p 8080:8080 --name cdd_debian cdd-python-all-debian
	sleep 3
	curl -X POST http://localhost:8080 -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "method": "missing", "id": 1}' || echo "container failed to respond"
	docker stop cdd_debian
	docker rm cdd_debian
