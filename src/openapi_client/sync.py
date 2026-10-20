"""Bidirectional OpenAPI and Arazzo directory synchronization orchestration."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from openapi_client.arazzo.emit import emit_arazzo_json
from openapi_client.arazzo.parse import parse_arazzo_json
from openapi_client.classes.emit import emit_models_module
from openapi_client.classes.parse import extract_classes_from_ast
from openapi_client.cli_sdk.emit import emit_cli_sdk
from openapi_client.cli_sdk.parse import extract_cli_from_ast
from openapi_client.dao.emit import emit_dao
from openapi_client.db.emit import emit_db
from openapi_client.functions.parse import extract_functions_from_ast
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import Components, Info, OpenAPI
from openapi_client.openapi.emit import emit_openapi_json
from openapi_client.openapi.parse import parse_openapi_json
from openapi_client.routes.emit import ClientGenerator
from openapi_client.scaffolding import write_generated
from openapi_client.seeder.emit import emit_seeder
from openapi_client.sqlalchemy_cdd.parse import parse_sqlalchemy_cdd
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.parse import extract_tests_from_ast
from openapi_client.workflows.emit import emit_workflows_code
from openapi_client.workflows.parse import extract_arazzo_from_code


def sync_dir(
    project_dir: str,
    truth: str | None = None,
    output_dir: str | None = None,
) -> None:
    """Synchronize an OpenAPI specification with source code in a directory.

    Args:
        project_dir: Path to the directory containing source files and/or `openapi.json`.
        truth: Optional single source of truth (`'openapi'`, `'class'`, `'function'`, `'sqlalchemy'`, `'arazzo'`, `'workflow'`).
        output_dir: Optional output directory; defaults to `project_dir`.
    """
    from openapi_client import cli as _cli

    d = Path(project_dir)
    out_d = Path(output_dir) if output_dir else d

    client_py = d / "src" / "client.py"
    if not client_py.exists():
        client_py = d / "client.py"

    models_py = d / "src" / "models.py"
    if not models_py.exists():
        models_py = d / "models.py"

    models_dir = (
        d / "src" / "models" if (d / "src" / "models").is_dir() else d / "models"
    )

    mock_py = d / "test" / "mock_server.py"
    if not mock_py.exists():
        mock_py = d / "mock_server.py"

    test_py = d / "test" / "test_client.py"
    if not test_py.exists():
        test_py = d / "test_client.py"

    cli_py = d / "src" / "cli_main.py"
    if not cli_py.exists():
        cli_py = d / "cli_main.py"
    openapi_json = d / "openapi.json"

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Extracted API", version="0.0.4"),
        paths={},
        components=Components(schemas={}),
    )

    if truth == "openapi" and openapi_json.exists():
        spec = parse_openapi_json(openapi_json.read_text(encoding="utf-8"))
    else:
        if client_py.exists() and truth in (None, "class", "function"):
            mod = cst.parse_module(client_py.read_text(encoding="utf-8"))
            if truth in (None, "class"):
                extract_classes_from_ast(mod, spec)
            if truth in (None, "function"):
                extract_functions_from_ast(mod, spec)

        if models_py.is_file() and truth in (None, "class", "sqlalchemy"):
            mod = cst.parse_module(models_py.read_text(encoding="utf-8"))
            parse_sqlalchemy_cdd(mod, spec)

        if models_dir.is_dir() and truth in (None, "sqlalchemy"):
            for sa_file in sorted(models_dir.glob("*.py")):
                if sa_file.name != "__init__.py":
                    mod = cst.parse_module(sa_file.read_text(encoding="utf-8"))
                    parse_sqlalchemy_cdd(mod, spec)

        if mock_py.exists() and truth in (None, "function"):
            mod = cst.parse_module(mock_py.read_text(encoding="utf-8"))
            extract_mocks_from_ast(mod, spec)

        if test_py.exists() and truth is None:
            mod = cst.parse_module(test_py.read_text(encoding="utf-8"))
            extract_tests_from_ast(mod, spec)

        if cli_py.exists() and truth is None:
            mod = cst.parse_module(cli_py.read_text(encoding="utf-8"))
            extract_cli_from_ast(mod, spec)

        if (
            openapi_json.exists()
            and not spec.paths
            and (
                spec.components is None or not getattr(spec.components, "schemas", None)
            )
        ):
            spec = parse_openapi_json(openapi_json.read_text(encoding="utf-8"))

    out_openapi_json = out_d / openapi_json.relative_to(d)
    out_openapi_json.parent.mkdir(parents=True, exist_ok=True)
    out_openapi_json.write_text(emit_openapi_json(spec, indent=2), encoding="utf-8")

    generator = ClientGenerator(spec)
    out_client_py = out_d / client_py.relative_to(d)
    out_client_py.parent.mkdir(parents=True, exist_ok=True)
    (out_client_py.parent / "__init__.py").touch(exist_ok=True)
    out_client_py.write_text(generator.generate_code(), encoding="utf-8")

    if spec.components and spec.components.schemas:
        out_models_py = out_d / models_py.relative_to(d)
        out_models_py.parent.mkdir(parents=True, exist_ok=True)
        (out_models_py.parent / "__init__.py").touch(exist_ok=True)
        out_models_py.write_text(
            emit_models_module(spec.components.schemas), encoding="utf-8"
        )

    out_test_py = out_d / test_py.relative_to(d)
    out_test_py.parent.mkdir(parents=True, exist_ok=True)
    (out_test_py.parent / "__init__.py").touch(exist_ok=True)
    out_test_py.write_text(emit_tests(spec).code, encoding="utf-8")

    out_mock_py = out_d / mock_py.relative_to(d)
    out_mock_py.parent.mkdir(parents=True, exist_ok=True)
    (out_mock_py.parent / "__init__.py").touch(exist_ok=True)
    out_mock_py.write_text(emit_mock_server(spec).code, encoding="utf-8")

    dao_fn = getattr(_cli, "emit_dao", emit_dao)
    write_generated(dao_fn(spec), "dao.py", base_dir=out_d)

    db_py = d / "src" / "db.py"
    if not db_py.exists():
        db_py = d / "db.py"

    out_db_py = out_d / db_py.relative_to(d)
    out_db_py.parent.mkdir(parents=True, exist_ok=True)
    out_db_py.write_text(emit_db(spec), encoding="utf-8")

    seeder_fn = getattr(_cli, "emit_seeder", emit_seeder)
    write_generated(seeder_fn(spec), "seeder.py", base_dir=out_d)

    if cli_py.exists():
        out_cli_py = out_d / cli_py.relative_to(d)
        out_cli_py.parent.mkdir(parents=True, exist_ok=True)
        (out_cli_py.parent / "__init__.py").touch(exist_ok=True)
        out_cli_py.write_text(emit_cli_sdk(spec), encoding="utf-8")

    arazzo_json = d / "arazzo.json"
    workflows_py = (
        d / "src" / "workflows.py"
        if (d / "src" / "workflows.py").exists()
        else d / "workflows.py"
    )

    if arazzo_json.exists() or workflows_py.exists():
        if truth == "arazzo" or not workflows_py.exists():
            arazzo_spec = parse_arazzo_json(
                arazzo_json.read_text(encoding="utf-8"), arazzo_json.parent
            )
        else:
            arazzo_spec = extract_arazzo_from_code(
                workflows_py.read_text(encoding="utf-8"), spec
            )
        out_arazzo = out_d / "arazzo.json"
        out_arazzo.write_text(emit_arazzo_json(arazzo_spec, indent=2), encoding="utf-8")
        out_wf = out_d / workflows_py.relative_to(d)
        out_wf.parent.mkdir(parents=True, exist_ok=True)
        out_wf.write_text(emit_workflows_code(arazzo_spec), encoding="utf-8")

    if out_d != d:
        print(f"Successfully synced {project_dir} to {output_dir}")
    else:
        print(f"Successfully synced {project_dir}")
