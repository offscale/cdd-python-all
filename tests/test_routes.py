"""Tests for ClientGenerator and client route round-trip parsing."""

from __future__ import annotations

import importlib
import os
import runpy
import sys
import unittest.mock
from pathlib import Path

import libcst as cst
import pytest

from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import OpenAPI, Schema
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.parse import extract_tests_from_ast


def test_extract_mock_and_test() -> None:
    """Test test_extract_mock_and_test."""
    mock_code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/pets")
def get_pets():
    """Summary

    Description
    """
    pass
'''
    mock_module = cst.parse_module(mock_code)
    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0"})
    extract_mocks_from_ast(mock_module, spec)
    assert spec.paths is not None
    op_pets = spec.paths["/pets"].get
    assert op_pets is not None
    assert op_pets.operationId == "get_pets"
    assert op_pets.summary == "Summary"
    assert op_pets.description == "Description"

    test_code = '''
def test_get_pets() -> None:
    """Test test_get_pets."""
    pass
'''
    test_module = cst.parse_module(test_code)
    extract_tests_from_ast(test_module, spec)


def test_parse_openapi() -> None:
    """Test test_parse_openapi."""
    spec_dict = {
        "openapi": "3.2.0",
        "info": {"title": "Example API", "version": "1.0.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "get_pets",
                    "responses": {"200": {"description": "pet response"}},
                }
            }
        },
    }

    spec = OpenAPI(**spec_dict)
    assert spec.openapi == "3.2.0"
    assert spec.info.title == "Example API"
    assert spec.paths is not None
    assert spec.paths["/pets"].get is not None
    assert spec.paths["/pets"].get.operationId == "get_pets"


def test_generate_code() -> None:
    """Test test_generate_code."""
    spec_dict = {
        "openapi": "3.2.0",
        "info": {"title": "Example API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "summary": "Pet summary",
                    "description": "A pet model",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string", "description": "Pet name"},
                        "price": {"type": "number"},
                        "is_friendly": {"type": "boolean"},
                    },
                },
                "Empty": {"type": "object"},
            }
        },
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "get_pets",
                    "summary": "Get all pets",
                    "description": "Returns a list of pets",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "pet response"}},
                },
                "post": {
                    "operationId": "create_pet",
                    "responses": {"201": {"description": "pet created"}},
                },
            }
        },
    }
    spec = OpenAPI(**spec_dict)
    generator = ClientGenerator(spec)
    code = generator.generate_code()
    assert "class Client" in code
    assert "def get_pets" in code
    assert "limit: int" in code

    from openapi_client.classes.emit import emit_models_module

    assert spec.components is not None
    assert spec.components.schemas is not None
    models_code = emit_models_module(spec.components.schemas)
    assert "class Pet(BaseModel):" in models_code
    assert "class Empty(BaseModel):" in models_code


def test_extract_code() -> None:
    """Test test_extract_code."""
    code = '''
class Pet(BaseModel):
    """A pet

    This represents a pet in the system.
    """
    id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    is_friendly: Optional[bool] = None

class Client:
    def get_pets(self):
        """Get all pets

        Returns all pets.
        """
        pass

    def post_pets(self):
        pass
'''
    spec = extract_from_code(code)
    assert spec.openapi == "3.2.0"
    assert spec.paths is not None
    assert spec.paths["/pets"].post is not None
    assert spec.paths["/pets"].post.operationId == "post_pets"

    # Direct test of ClassExtractor with missing components
    import libcst as cst

    from openapi_client.classes.parse import ClassExtractor

    empty_spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    visitor = ClassExtractor(empty_spec)
    cst.parse_module("class Empty: pass").visit(visitor)
    assert empty_spec.components is not None
    assert spec.paths["/pets"].get is not None
    assert spec.paths["/pets"].get.operationId == "get_pets"
    assert spec.paths["/pets"].get.summary == "Get all pets"
    assert spec.paths["/pets"].get.description == "Returns all pets."

    assert spec.components is not None
    assert spec.components.schemas is not None
    assert "Pet" in spec.components.schemas
    pet_schema = spec.components.schemas["Pet"]
    assert isinstance(pet_schema, Schema)
    assert pet_schema.summary == "A pet"
    assert pet_schema.description == "This represents a pet in the system."
    assert pet_schema.properties is not None
    assert getattr(pet_schema.properties["id"], "type", None) == "integer"
    assert getattr(pet_schema.properties["name"], "type", None) == "string"
    assert getattr(pet_schema.properties["price"], "type", None) == "number"
    assert getattr(pet_schema.properties["is_friendly"], "type", None) == "boolean"


def test_emit_tests_and_mocks() -> None:
    """Test test_emit_tests_and_mocks."""
    spec_dict = {
        "openapi": "3.2.0",
        "info": {"title": "Example API", "version": "1.0.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "get_pets",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "create_pet",
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    },
                    "responses": {"201": {"description": "Created"}},
                },
                "put": {
                    "operationId": "update_pet",
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "operationId": "delete_pet",
                    "responses": {"204": {"description": "No Content"}},
                },
                "patch": {
                    "operationId": "patch_pet",
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }
    spec = OpenAPI(**spec_dict)

    # Test emit_tests
    test_module = emit_tests(spec)
    code = test_module.code
    assert "import pytest" in code

    # Check GET (no body)
    assert "def test_get_pets():" in code
    assert "response = client.get_pets()" in code

    # Check POST (with body)
    assert "def test_create_pet():" in code
    assert "response=client.create_pet(body={})" in code.replace(" ", "")

    # Check other methods
    assert "def test_update_pet():" in code
    assert "response = client.update_pet()" in code
    assert "def test_delete_pet():" in code
    assert "response = client.delete_pet()" in code
    assert "def test_patch_pet():" in code
    assert "response = client.patch_pet()" in code

    # Check response assertion
    assert "assert response is not None" in code

    # Test emit_mock_server
    mock_module = emit_mock_server(spec)
    code = mock_module.code
    assert "from fastapi import FastAPI" in code
    assert '@app.get("/pets")' in code
    assert "def get_pets():" in code
    assert '@app.post("/pets")' in code
    assert "def create_pet():" in code

    # Test emit_tests composable
    composable_module = emit_tests(spec, composable=True)
    comp_code = composable_module.code
    assert "@pytest.fixture" in comp_code
    assert "def client():" in comp_code
    assert "return Client(" in comp_code

    # Check that tests accept the fixture
    assert "def test_get_pets(client):" in comp_code
    assert "response=client.get_pets()" in comp_code.replace(" ", "")


def test_mock_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test executing test/mock_server.py with a mocked FastAPI module.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setitem(sys.modules, "fastapi", unittest.mock.MagicMock())
    mock_server_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../test/mock_server.py")
    )
    res = runpy.run_path(mock_server_path)
    assert "app" in res


def test_test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test test_client module execution in an isolated temporary workspace.

    Args:
        tmp_path: Temporary directory path fixture.
        monkeypatch: Pytest monkeypatch fixture.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "client.py").write_text(
        '"""Client stub."""\n\n\nclass Client:\n    """Client."""\n\n    def __init__(self, *args, **kwargs) -> None:\n        """Init."""\n        pass\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(src_dir))

    import test.test_client as tc

    importlib.reload(tc)
    tc.test_client()


def test_execute_generated_client_http_requests() -> None:
    """Execute generated Client class with a mock PoolManager and verify request arguments."""
    from typing import Any

    from openapi_client.openapi.parse import parse_openapi_dict

    spec_dict = {
        "openapi": "3.2.0",
        "info": {"title": "Petstore", "version": "1.0.0"},
        "paths": {
            "/pets/{pet_id}": {
                "get": {
                    "operationId": "getPet",
                    "parameters": [
                        {"name": "pet_id", "in": "path", "schema": {"type": "integer"}},
                        {
                            "name": "tags",
                            "in": "query",
                            "style": "form",
                            "explode": True,
                            "schema": {"type": "array", "items": {"type": "string"}},
                        },
                        {
                            "name": "space_tags",
                            "in": "query",
                            "style": "spaceDelimited",
                            "explode": False,
                            "schema": {"type": "array", "items": {"type": "string"}},
                        },
                        {
                            "name": "pipe_tags",
                            "in": "query",
                            "style": "pipeDelimited",
                            "explode": False,
                            "schema": {"type": "array", "items": {"type": "string"}},
                        },
                    ],
                },
                "post": {
                    "operationId": "updatePetForm",
                    "parameters": [
                        {"name": "pet_id", "in": "path", "schema": {"type": "integer"}},
                        {
                            "name": "name",
                            "in": "formData",
                            "schema": {"type": "string"},
                        },
                    ],
                },
                "put": {
                    "operationId": "replacePet",
                    "parameters": [
                        {"name": "pet_id", "in": "path", "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    },
                },
            }
        },
    }
    spec = parse_openapi_dict(spec_dict)
    code = ClientGenerator(spec).generate_code()
    ns: dict[str, Any] = {}
    exec(compile(code, "<client>", "exec"), ns)  # noqa: S102
    client_cls = ns["Client"]

    client = client_cls(base_url="https://api.example.com", api_key="secret-token")
    mock_http = unittest.mock.MagicMock()
    client.http = mock_http

    expected_headers = {
        "api_key": "secret-token",
        "Authorization": "Bearer secret-token",
    }

    client.get_pet(10, "available", ["c", "d"], ["e", "f"])
    mock_http.request.assert_called_with(
        "GET",
        "https://api.example.com/pets/10?tags=available&space_tags=c d&pipe_tags=e|f",
        headers=expected_headers,
    )

    client.update_pet_form(10, "Fluffy")
    mock_http.request.assert_called_with(
        "POST",
        "https://api.example.com/pets/10",
        headers=expected_headers,
        fields={"name": "Fluffy"},
    )

    client.replace_pet(10, body={"status": "sold"})
    mock_http.request.assert_called_with(
        "PUT",
        "https://api.example.com/pets/10",
        headers=expected_headers,
        json={"status": "sold"},
    )

    with client as ctx_client:
        assert ctx_client is client
    mock_http.clear.assert_called_once()

    # Test additionalOperations round-trip
    from openapi_client.models import Operation, PathItem
    from openapi_client.routes.parse import extract_from_code

    custom_spec = parse_openapi_dict(
        {
            "openapi": "3.2.0",
            "info": {"title": "Custom Verb API", "version": "1.0.0"},
            "paths": {},
        }
    )
    assert custom_spec.paths is not None
    custom_spec.paths["/items"] = PathItem(
        additionalOperations={
            "COPY": Operation(operationId="copy_items", summary="Copy items"),
            "LOCK": Operation(operationId="lock_items", summary="Lock items"),
        }
    )
    custom_code = ClientGenerator(custom_spec).generate_code()
    assert "def copy_items" in custom_code
    assert "def lock_items" in custom_code
    extracted_custom = extract_from_code(custom_code)
    assert extracted_custom.paths is not None
    assert "/items" in extracted_custom.paths
    assert extracted_custom.paths["/items"].additionalOperations is not None
    assert "COPY" in extracted_custom.paths["/items"].additionalOperations
    assert "LOCK" in extracted_custom.paths["/items"].additionalOperations
