# Developing

Welcome to the `cdd-python-client` development guide. This project is built using Python 3.9+ and relies heavily on AST manipulation using `libcst`.

## Setup

1. **Clone and Setup Virtual Environment:**
   ```bash
   git clone <repository_url>
   cd cdd-python-client
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies (Including Dev):**
   ```bash
   pip install -e .[dev]
   ```
   *Note: This will install `pydantic`, `libcst`, `urllib3`, `pytest`, `pytest-cov`, and `mypy`.*

## Running Tests

We maintain **100% test coverage**. Any new features must be fully covered.

```bash
# Run pytest with coverage reporting
PYTHONPATH=src pytest --cov=src --cov-report=term-missing
```

## Type Checking

We maintain **100% Type Safety**. All modules must pass strict mypy validation.

```bash
mypy src/openapi_client
```

## Extending the Architecture

The codebase relies on a pattern of `parse.py` (AST to Spec) and `emit.py` (Spec to AST) inside domain-specific directories (`src/openapi_client/<domain>/`).

### Adding a New Domain
1. **Create the directory**: `mkdir src/openapi_client/new_domain/`
2. **Create `parse.py`**:
   - Write a `libcst.CSTVisitor` subclass to traverse Python AST and mutate the shared `OpenAPI` state model.
3. **Create `emit.py`**:
   - Write functions that take an `OpenAPI` state model and return `libcst.CSTNode` objects (like `cst.ClassDef` or `cst.FunctionDef`).
4. **Wire into `cli.py`**:
   - Make sure your extractor is called inside `sync_dir()` and `extract_from_code()`.
   - Make sure your emitter is called when assembling the client module.

### Updating Models
Models are located in `src/openapi_client/models.py`. We use `pydantic`. If you add self-referencing schemas or complex union types, ensure you update the `model_rebuild()` calls at the bottom of the file.
