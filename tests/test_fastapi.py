"""Tests for FastAPI server emission, README emission, and FastAPI AST parsing."""

from __future__ import annotations

import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

import libcst as cst
import pytest
from libcst._nodes.base import CSTValidationError

from openapi_client.classes.emit import _schema_to_type_annotation
from openapi_client.cli import (
    generate_from_openapi,
    generate_to_openapi,
    main,
    run_mcp_server,
    sync_dir,
)
from openapi_client.cli_sdk_cdd.parse import parse_cli_sdk_cdd
from openapi_client.fastapi.emit import emit_fastapi
from openapi_client.fastapi.emit_readme import emit_readme
from openapi_client.fastapi.parse import extract_fastapi_from_ast
from openapi_client.functions.emit import emit_functions
from openapi_client.functions.parse import (
    _extract_schema_from_annotation,
    extract_functions_from_ast,
)
from openapi_client.functions.utils import get_default_server_url
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import (
    Components,
    Info,
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
    Server,
)
from openapi_client.openapi.parse import resolve_external_refs
from openapi_client.seeder.emit import emit_seeder
from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy
from openapi_client.sqlalchemy_cdd.parse import parse_sqlalchemy_cdd
from openapi_client.tests.emit import (
    emit_operation_test,
    get_dummy_value_for_schema,
    get_stub_body,
)
from openapi_client.tests.emit_server_tests import emit_server_tests
from openapi_client.tests.parse import extract_tests_from_ast


def test_emit_readme():
    """Test emit_readme with empty spec."""
    spec = OpenAPI(info={"title": "Test Title", "version": "1.0"}, openapi="3.2.0")
    code = emit_readme(spec)

    assert "# Test Title" in code
    assert "### 1. Stub Mode" in code
    assert "### 4. Full Mock Mode" in code
    assert "--ephemeral --seed" in code


def test_fastapi_parse_edge_cases() -> None:
    """Test extract_fastapi_from_ast on malformed and valid route decorators."""
    code = """
@app.get() # No args
@app.get(path_var) # Not a simple string
@app.unknown("/path") # Not a valid method
@foo.get("/path") # Not app
@app("something") # Not an attribute
@unknown # Not a call
def something():
    pass
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0"}, paths={})
    spec.paths["/existing"] = PathItem()
    code2 = """@app.get("/existing")
def existing():
    \"\"\"Existing summary.\n\nExisting description.\"\"\"
    pass
"""
    extract_fastapi_from_ast(module, spec)

    spec.paths["/existing"].get = Operation(operationId="mock")
    extract_fastapi_from_ast(cst.parse_module(code2), spec)
    assert spec.paths["/existing"].get is not None
    assert spec.paths["/existing"].get.operationId == "existing"
    assert spec.paths["/existing"].get.summary == "Existing summary."


def test_functions_emit_edge_cases() -> None:
    """Test emit_functions when path or parameters have edge-case values."""
    p1 = Parameter(name="", **{"in": "body"})
    p2 = Parameter(name="", **{"in": "query"})
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "Test", "version": "1.0"},
        paths={
            "invalid_path": PathItem(get=Operation(operationId="invalid")),
            "/valid": PathItem(
                get=Operation(operationId="test_body_no_name", parameters=[p1, p2]),
                post=None,
            ),
        },
    )
    with pytest.raises(CSTValidationError):
        emit_functions(spec)


def test_functions_parse_edge_cases() -> None:
    """Test extract_functions_from_ast with complex annotations and body expressions."""
    ann_any = cst.Annotation(annotation=cst.Name("Any"))
    assert _extract_schema_from_annotation(ann_any).type == "string"

    code = """
from typing import List, Dict, Tuple
@deprecated
@tags(["tag1", 123])
@tags()
@tags(not_a_list)
@unknown
@app.route()
def get_something(
    p1: List[int],
    p2: List,
    p3: Dict[str, str],
    p4: Tuple[int]
) -> List:
    other = 1
    url = self.base_url + "/simple"
    url = self.base_url + f"/items/{p1}/details" + ("?" if True else "")
    url = self.base_url + 123
    url = 123
    response = self.http.request("GET", url)
    self.http.request(123, url)
    return response
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0"}, paths={})
    extract_functions_from_ast(module, spec)
    assert "/items/{p1}/details" in spec.paths
    op = spec.paths["/items/{p1}/details"].get
    assert op is not None
    assert op.deprecated is True
    assert op.tags == ["tag1"]


def test_mocks_parse_edge_cases() -> None:
    """Test extract_mocks_from_ast on edge-case decorators and return statements."""
    code = """
@app.get()
@app.get(path_var)
@app.unknown("/path")
@foo.get("/path")
@app("something")
@unknown
def something():
    return EventSourceResponse()
    return other()
    return EventSourceResponse
    return app.EventSourceResponse()
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0"}, paths={})
    extract_mocks_from_ast(module, spec)
    assert spec.paths == {}

    spec.paths = None
    extract_mocks_from_ast(module, spec)
    assert spec.paths == {}


def test_cli_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI edge cases including truth options and write_generated branches."""
    with mock.patch("sys.argv", ["cli.py", "serve_json_rpc", "--port", "1234"]):
        with mock.patch("openapi_client.cli.serve_json_rpc") as mock_run:
            main()
            mock_run.assert_called_once()

    with tempfile.TemporaryDirectory() as d, mock.patch(
        "sys.argv", ["cli.py", "from_openapi", "to_unknown", "--input-dir", d]
    ), pytest.raises(SystemExit):
        main()

    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "src").mkdir()
        (p / "test").mkdir()
        (p / "src" / "client.py").write_text(
            """class Client:
    def get_pets(self):
        pass
""",
            encoding="utf-8",
        )
        (p / "src" / "models.py").write_text(
            """from pydantic import BaseModel
class Pet(BaseModel):
    id: int
""",
            encoding="utf-8",
        )
        (p / "test" / "mock_server.py").touch()
        (p / "test" / "test_client.py").touch()
        (p / "src" / "cli_main.py").touch()
        (p / "src" / "db.py").touch()
        (p / "openapi.json").write_text(
            '{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}',
            encoding="utf-8",
        )

        sync_dir(d)
        sync_dir(d, truth="openapi")
        sync_dir(d, truth="class")
        sync_dir(d, truth="function")
        assert (p / "openapi.json").exists()

    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "src").mkdir()
        (p / "test").mkdir()
        (p / "src" / "client.py").touch()
        (p / "src" / "models.py").touch()
        (p / "test" / "mock_server.py").touch()
        (p / "test" / "test_client.py").touch()
        (p / "src" / "cli_main.py").touch()
        generate_to_openapi(d, str(p / "output.json"))
        assert (p / "output.json").exists()

    # Unknown method without req_id in run_mcp_server
    inputs = '{"jsonrpc": "2.0", "method": "unknown_notification"}\n{"jsonrpc": "2.0", "method": "close", "id": 1}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", StringIO())
    run_mcp_server()


def test_cli_param_no_name() -> None:
    """Test generate_from_openapi when parameter name is empty."""
    spec_json = """
    {
        "openapi": "3.2.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/test": {
                "get": {
                    "operationId": "test_op",
                    "parameters": [{ "name": "", "in": "query", "schema": {"type": "string"} }]
                }
            },
            "/no-methods": {}
        }
    }
    """
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "spec.json").write_text(spec_json, encoding="utf-8")
        with pytest.raises(CSTValidationError):
            generate_from_openapi(
                "to_sdk", str(p / "spec.json"), None, d, False, False, False
            )


def test_openapi_parse_edge_cases(tmp_path: Path) -> None:
    """Test resolve_external_refs cycle detection and non-file refs."""
    f1 = tmp_path / "cycle.json"
    f1.write_text('{"$ref": "cycle.json"}', encoding="utf-8")
    res = resolve_external_refs({"$ref": "cycle.json"}, base_path=tmp_path)
    assert res == {"$ref": "cycle.json"}

    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="T", version="1"),
        servers=[Server(url="")],
    )
    assert get_default_server_url(spec, fallback="http://fallback") == "http://fallback"


def test_sqlalchemy_and_cli_cdd_parse_edge_cases() -> None:
    """Test parse_sqlalchemy_cdd, parse_cli_sdk_cdd, and emit_sqlalchemy edge cases."""
    spec = OpenAPI(
        openapi="3.2.0",
        info=Info(title="T", version="1"),
        components=Components(schemas={}),
        paths={"/pets": PathItem(get=Operation(operationId="get_pets"))},
    )
    mod_cls = cst.parse_module("""class User(Base):
    id: int
""")
    parse_sqlalchemy_cdd(mod_cls, spec)
    assert spec.components is not None
    assert "User" in (spec.components.schemas or {})

    mod_cli = cst.parse_module(
        'subparsers.add_parser("get_pets", help="Get all pets")\n'
    )
    parse_cli_sdk_cdd(mod_cli, spec)
    assert spec.paths["/pets"].get.summary == "Get all pets"

    sa_files = emit_sqlalchemy(spec)
    assert "models/user.py" in sa_files


def test_mocks_and_tests_emit_parse_edge_cases(tmp_path: Path) -> None:
    """Test remaining branches in classes, tests, fastapi, and seeder modules."""
    assert (
        _schema_to_type_annotation(Reference(**{"$ref": "#/components/schemas/123bad"}))
        == "Any"
    )
    assert _schema_to_type_annotation(Schema(type="object")) == "dict[str, Any]"

    assert (
        get_dummy_value_for_schema(Schema(type="boolean", example=True)).value == "True"
    )
    assert get_dummy_value_for_schema(Schema(type="integer", default=42)).value == "42"
    assert (
        get_dummy_value_for_schema(Schema(type="number", example=3.14)).value == "3.14"
    )
    assert (
        get_dummy_value_for_schema(Schema(type="string", enum=["active"])).value
        == '"active"'
    )
    assert (
        get_dummy_value_for_schema(Schema(type="string", format="uri")).value
        == '"http://example.com"'
    )

    stub_arr = get_stub_body(
        Schema(
            type="object",
            properties={
                "tags": Schema(type="array", items=Schema(type="string")),
                "nested": Schema(
                    type="object", properties={"a": Schema(type="integer")}
                ),
            },
        )
    )
    assert isinstance(stub_arr, cst.Dict)

    op_200 = Operation(
        operationId="list_items",
        responses={"200": Response(description="ok")},
    )
    fn_200 = emit_operation_test("get", "/items", op_200, composable=True)
    assert fn_200.name.value == "test_list_items"

    op_custom_media = Operation(
        operationId="upload_text",
        requestBody=RequestBody(
            content={"text/plain": MediaType(schema=Schema(type="string"))}
        ),
    )
    fn_media = emit_operation_test("post", "/upload", op_custom_media, composable=False)
    assert fn_media.name.value == "test_upload_text"

    spec_sse = OpenAPI(
        openapi="3.2.0",
        info=Info(title="T", version="1"),
        paths={
            "/other": PathItem(post=Operation(operationId="other_op")),
            "/events": PathItem(get=Operation(operationId="stream_events")),
        },
    )
    test_code = """
def test_stream_events():
    res = "text/event-stream"

def stream_new_endpoint():
    res = "text/event-stream"
"""
    extract_tests_from_ast(cst.parse_module(test_code), spec_sse)
    assert spec_sse.paths["/events"].get.responses is not None
    assert "/stream_new_endpoint" in spec_sse.paths

    extract_tests_from_ast(cst.parse_module(test_code), spec_sse)

    spec_none_paths = OpenAPI.model_construct(
        openapi="3.2.0", info=Info(title="T", version="1"), paths=None
    )
    extract_tests_from_ast(cst.parse_module(test_code), spec_none_paths)
    assert spec_none_paths.paths is not None

    spec_fa = OpenAPI(
        openapi="3.2.0",
        info=Info(title="T", version="1"),
        paths={
            "": PathItem(get=Operation(operationId="empty_path")),
            "/": PathItem(get=Operation(operationId="root_get")),
            "/users": PathItem(get=Operation(operationId="get_users")),
            "/users/profile": PathItem(get=Operation(operationId="get_profile")),
        },
        components=Components(
            schemas={"EmptyModel": Schema(type="object", properties=None)}
        ),
    )
    fa_files = emit_fastapi(spec_fa)
    assert "routes/default.py" in fa_files
    assert "routes/users.py" in fa_files

    seeder_files = emit_seeder(spec_fa)
    assert "mocks/factories.py" in seeder_files

    spec_no_get = OpenAPI(
        openapi="3.2.0",
        info=Info(title="T", version="1"),
        paths={"/users": PathItem(post=Operation(operationId="create_user"))},
        components=Components(
            schemas={
                "User": Schema(type="object", properties={"id": Schema(type="integer")})
            }
        ),
    )
    srv_tests = emit_server_tests(spec_no_get)
    assert "No GET endpoints found in spec" in srv_tests["test_stub.py"]

    spec_empty_paths = OpenAPI(
        openapi="3.2.0",
        info=Info(title="T", version="1"),
        paths=None,
        components=Components(
            schemas={
                "User": Schema(type="object", properties={"id": Schema(type="integer")})
            }
        ),
    )
    srv_tests_empty = emit_server_tests(spec_empty_paths)
    assert "No GET endpoints found in spec" in srv_tests_empty["test_stub.py"]

    mock_mod = emit_mock_server(spec_no_get)
    assert "def create_user" in mock_mod.code

    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        '{"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}',
        encoding="utf-8",
    )
    with mock.patch("openapi_client.cli.emit_dao", return_value="single_file_dao = 1"):
        generate_from_openapi(
            "to_sdk", str(spec_file), None, str(tmp_path / "out_s"), True, True, True
        )
        assert (tmp_path / "out_s" / "test" / "dao.py").exists()

    with mock.patch("openapi_client.cli.emit_dao", return_value=""):
        generate_from_openapi(
            "to_sdk", str(spec_file), None, str(tmp_path / "out_e"), True, True, True
        )

    with mock.patch("openapi_client.cli.emit_dao", return_value={"empty.py": ""}):
        generate_from_openapi(
            "to_sdk", str(spec_file), None, str(tmp_path / "out_d"), True, True, True
        )

    with mock.patch("openapi_client.cli.emit_seeder", return_value=""), mock.patch(
        "openapi_client.cli.emit_dao", return_value={"empty_dao.py": ""}
    ):
        sync_dir(str(tmp_path / "out_s"))
