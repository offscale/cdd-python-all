"""Emit README.md for the generated server."""

from openapi_client.models import OpenAPI


def emit_readme(spec: OpenAPI) -> str:
    """Generate the README.md documenting the server modes."""
    title = spec.info.title if spec and spec.info else "Generated CDD Server"

    lines = [
        f"# {title}",
        "",
        "This is an orthogonal, multi-tiered CDD Server generated from an OpenAPI specification.",
        "",
        "## Decoupled Server Modes",
        "",
        "You can run the server in several distinct modes depending on your testing or production needs:",
        "",
        "### 1. Stub Mode",
        "- **Command:** `python main.py` (with no DATABASE_URL configured)",
        "- **Description:** The server runs using traditional scaffolds. Endpoints safely return `NotImplementedError` or empty bodies.",
        "",
        "### 2. Production Mode",
        "- **Command:** `DATABASE_URL=postgres://... python main.py`",
        "- **Description:** Uses actual ORM interactions against a real database.",
        "",
        "### 3. Sandbox Mode",
        "- **Command:** `python main.py --ephemeral`",
        "- **Description:** Uses actual ORM interactions against a fresh, throwaway SQLite in-memory database.",
        "",
        "### 4. Full Mock Mode",
        "- **Command:** `python main.py --ephemeral --seed`",
        "- **Description:** Ephemeral database, automatically populated with a localized fake data graph using Faker.",
        "",
        "## Testing",
        "",
        "The generated codebase includes comprehensive category tests ensuring 100% test coverage across all DAOs and the generated HTTP server endpoints.",
        "Run tests using `pytest`.",
        "",
        "## Unified CLI Toolset",
        "",
        "This project comes with a unified CLI toolset for contract conformance and bi-directional synchronization.",
        "Use the `cdd-python` (or `cdd-python-all`) executable:",
        "",
        "- **`from_openapi`**: Generate artifacts from an OpenAPI specification.",
        "  - `to_server`: Generate the server code (including DAOs, models, routing, and this README).",
        "  - `to_sdk`: Generate the client SDK.",
        "  - `to_sdk_cli`: Generate the client SDK with a CLI interface.",
        "- **`to_openapi`**: Reverse-generate the OpenAPI specification from your running code (models and functions).",
        "- **`sync`**: Bidirectionally synchronize changes between models, DAOs, and specs.",
        "  - Use `--truth <SOURCE>` (e.g., `--truth class`, `--truth sqlalchemy`, `--truth function`) to designate the single source of truth and propagate changes to prevent contract drift.",
        "",
    ]

    return "\n".join(lines)
