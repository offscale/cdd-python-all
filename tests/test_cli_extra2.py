"""Tests for test_cli_extra2.py."""

import json
from openapi_client.cli import generate_from_openapi


def test_cli_output_file(tmp_path):
    """Test test_cli_output_file."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_file = tmp_path / "out" / "client.py"
    generate_from_openapi("to_sdk", str(spec_path), None, str(out_file))

    assert (tmp_path / "out" / "src" / "client.py").exists()


def test_cli_to_server_with_models(tmp_path):
    """Test test_cli_to_server_with_models."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_server"
    generate_from_openapi("to_server", str(spec_path), None, str(out_dir))

    assert (out_dir / "main.py").exists()
    assert (out_dir / "models" / "pet.py").exists()


def test_cli_to_sdk_cli_cdd(tmp_path, monkeypatch):
    """Test test_cli_to_sdk_cli_cdd."""
    import ast

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "getPets",
                    "summary": "Get all pets",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema_": {"type": ["integer", "null"]},
                            "required": True,
                        }
                    ],
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_sdk_cli"
    generate_from_openapi("to_sdk_cli", str(spec_path), None, str(out_dir), tests=True)

    assert (out_dir / "src" / "cli_main.py").exists()

    # Now make ast.unparse fail to cover the except block in cli_sdk_cdd/emit.py
    def mock_unparse(*args, **kwargs):
        """Test mock_unparse."""
        raise Exception("Mock error")

    monkeypatch.setattr(ast, "unparse", mock_unparse)
    generate_from_openapi("to_sdk_cli", str(spec_path), None, str(out_dir))


def test_cli_to_server_sqlalchemy_ast_fail(tmp_path, monkeypatch):
    """Test test_cli_to_server_sqlalchemy_ast_fail."""
    import ast

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "id": {"type": ["integer"]},
                        "name": {"type": ["string", "null"]},
                    },
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_server2"

    def mock_unparse(*args, **kwargs):
        """Test mock_unparse."""
        raise Exception("Mock error")

    monkeypatch.setattr(ast, "unparse", mock_unparse)
    generate_from_openapi("to_server", str(spec_path), None, str(out_dir))


def test_fastapi_emit(tmp_path):
    """Test test_fastapi_emit."""
    from openapi_client.fastapi.emit import emit_fastapi
    from openapi_client.models import OpenAPI, Info, PathItem, Operation

    spec = OpenAPI(
        openapi="3.0.0",
        info=Info(title="Test", version="1.0", description="Desc"),
        paths={
            "/test": PathItem(
                get=Operation(summary="sum", description="desc"),
                post=Operation(operationId="post_test"),
            )
        },
    )
    code = emit_fastapi(spec)
    assert "main.py" in code
    assert "@router.get('/test')" in code["routes/test.py"]

    assert "def get_test():" in code["routes/test.py"]
    assert "def post_test():" in code["routes/test.py"]


def test_fastapi_parse():
    """Test test_fastapi_parse."""
    import libcst as cst
    from openapi_client.fastapi.parse import extract_fastapi_from_ast
    from openapi_client.models import OpenAPI

    code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/hello")
def hello():
    pass
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.0.0", info={"title": "T", "version": "1"})
    extract_fastapi_from_ast(module, spec)
    assert "/hello" in spec.paths
    assert "get" in spec.paths["/hello"]
    assert spec.paths["/hello"]["get"]["operationId"] == "get_hello"


def test_sqlalchemy_cdd_emit_no_components(tmp_path):
    """Test test_sqlalchemy_cdd_emit_no_components."""
    from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy
    from openapi_client.models import OpenAPI

    spec = OpenAPI(openapi="3.0.0", info={"title": "Test", "version": "1.0"})
    res = emit_sqlalchemy(spec)
    assert res == {}
