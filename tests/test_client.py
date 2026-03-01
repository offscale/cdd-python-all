import pytest
import json
import libcst as cst
from openapi_client.models import OpenAPI, Schema, Components, Operation, PathItem
from openapi_client.routes.emit import ClientGenerator
from openapi_client.routes.parse import extract_from_code
from openapi_client.classes.emit import emit_classes, emit_class
from openapi_client.classes.parse import extract_classes_from_ast
from openapi_client.docstrings.emit import emit_class_docstring, emit_function_docstring
from openapi_client.docstrings.parse import parse_docstring
from openapi_client.functions.emit import emit_function, emit_functions
from openapi_client.functions.parse import extract_functions_from_ast
from openapi_client.tests.emit import emit_tests
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.tests.parse import extract_tests_from_ast


def test_extract_mock_and_test():
    mock_code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/pets")
def get_pets():
    \"\"\"Summary

    Description
    \"\"\"
    pass
"""
    mock_module = cst.parse_module(mock_code)
    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0"})
    extract_mocks_from_ast(mock_module, spec)
    assert spec.paths["/pets"].get.operationId == "get_pets"
    assert spec.paths["/pets"].get.summary == "Summary"
    assert spec.paths["/pets"].get.description == "Description"

    test_code = """
def test_get_pets():
    pass
"""
    test_module = cst.parse_module(test_code)
    extract_tests_from_ast(test_module, spec)


def test_parse_openapi():
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
    assert spec.paths["/pets"].get.operationId == "get_pets"


def test_generate_code():
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
    assert "class Pet(BaseModel):" in code
    assert "class Empty(BaseModel):" in code
    assert "limit: int" in code


def test_extract_code():
    code = """
class Pet(BaseModel):
    \"\"\"A pet

    This represents a pet in the system.
    \"\"\"
    id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    is_friendly: Optional[bool] = None

class Client:
    def get_pets(self):
        \"\"\"Get all pets

        Returns all pets.
        \"\"\"
        pass

    def post_pets(self):
        pass
"""
    spec = extract_from_code(code)
    assert spec.openapi == "3.2.0"
    assert spec.paths["/pets"].post.operationId == "post_pets"

    # Direct test of ClassExtractor with missing components
    import libcst as cst
    from openapi_client.classes.parse import ClassExtractor

    empty_spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    visitor = ClassExtractor(empty_spec)
    cst.parse_module("class Empty: pass").visit(visitor)
    assert empty_spec.components is not None
    assert spec.paths["/pets"].get.operationId == "get_pets"
    assert spec.paths["/pets"].get.summary == "Get all pets"
    assert spec.paths["/pets"].get.description == "Returns all pets."

    assert "Pet" in spec.components.schemas
    pet_schema = spec.components.schemas["Pet"]
    assert pet_schema.summary == "A pet"
    assert pet_schema.description == "This represents a pet in the system."
    assert pet_schema.properties["id"].type == "integer"
    assert pet_schema.properties["name"].type == "string"
    assert pet_schema.properties["price"].type == "number"
    assert pet_schema.properties["is_friendly"].type == "boolean"


def test_emit_tests_and_mocks():
    spec_dict = {
        "openapi": "3.2.0",
        "info": {"title": "Example API", "version": "1.0.0"},
        "paths": {"/pets": {"get": {"operationId": "get_pets"}}},
    }
    spec = OpenAPI(**spec_dict)

    # Test emit_tests
    test_module = emit_tests(spec)
    code = test_module.code
    assert "import pytest" in code
    assert "def test_get_pets():" in code
    assert 'Client("http://localhost")' in code

    # Test emit_mock_server
    mock_module = emit_mock_server(spec)
    code = mock_module.code
    assert "from fastapi import FastAPI" in code
    assert '@app.get("/pets")' in code
    assert "def get_pets():" in code
