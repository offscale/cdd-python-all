import pytest
from openapi_client.models import OpenAPI, Schema, Reference, Components
from openapi_client.classes.emit import emit_classes
from openapi_client.classes.parse import ClassExtractor
from openapi_client.functions.parse import FunctionExtractor
from openapi_client.mocks.parse import MockServerExtractor
import libcst as cst


def test_classes_emit_ref():
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        components={
            "schemas": {
                "MyClass": Schema(
                    **{
                        "type": "object",
                        "properties": {
                            "my_ref": Reference(
                                **{"$ref": "#/components/schemas/Other"}
                            )
                        },
                    }
                )
            }
        },
    )
    defs = emit_classes(spec.components.schemas)
    assert len(defs) == 1


def test_classes_parse_empty_components():
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        components=Components(),
    )
    extractor = ClassExtractor(spec)
    module = cst.parse_module("class MyClass:\n    pass\n")
    module.visit(extractor)
    assert "MyClass" in spec.components.schemas


def test_functions_parse_empty_paths():
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = FunctionExtractor(spec)
    module = cst.parse_module("def get_pets():\n    pass\n")
    module.visit(extractor)
    assert "/pets" in spec.paths


def test_mocks_parse_empty_paths():
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = MockServerExtractor(spec)
    module = cst.parse_module("@app.get('/pets')\ndef my_mock():\n    pass\n")
    module.visit(extractor)
    assert "/pets" in spec.paths


import pytest
from openapi_client.models import OpenAPI, Schema, Reference, Components
from openapi_client.functions.parse import FunctionExtractor
import libcst as cst


def test_functions_parse_full_features():
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = FunctionExtractor(spec)
    code = """
@tags(['Users'])
@deprecated
def post_user(user_id: str, limit: int = 10, is_active: bool = True, ratio: float = 1.0, tags: list[str] = [], extra: dict[str, str] = {}, data: MyBody = None) -> MyResponse:
    '''
    Create User

    Creates a new user object.
    '''
    pass
"""
    module = cst.parse_module(code)
    module.visit(extractor)

    op = spec.paths["/user"].post
    assert op.operationId == "post_user"
    assert op.summary == "Create User"
    assert op.description == "Creates a new user object."
    assert op.deprecated is True
    assert "Users" in op.tags

    # Check parameters
    assert len(op.parameters) == 6
    params = {p.name: p for p in op.parameters}
    assert params["user_id"].in_ == "path"
    assert params["user_id"].required is True
    assert params["user_id"].schema_.type == "string"

    assert params["limit"].in_ == "query"
    assert params["limit"].required is False
    assert params["limit"].schema_.type == "integer"

    assert params["is_active"].schema_.type == "boolean"
    assert params["ratio"].schema_.type == "number"
    assert params["tags"].schema_.type == "array"
    assert params["tags"].schema_.items.type == "string"

    assert params["extra"].schema_.type == "object"

    # Check request body
    assert op.requestBody is not None
    assert op.requestBody.required is False
    assert (
        op.requestBody.content["application/json"].schema_.ref
        == "#/components/schemas/MyBody"
    )

    # Check response
    assert op.responses is not None
    assert (
        op.responses["200"].content["application/json"].schema_.ref
        == "#/components/schemas/MyResponse"
    )


import pytest
from openapi_client.models import OpenAPI
from openapi_client.functions.parse import FunctionExtractor
import libcst as cst


def test_functions_parse_fallback_annotation():
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = FunctionExtractor(spec)
    code = """
def post_user(arg: "ForwardRef"):
    pass
"""
    module = cst.parse_module(code)
    module.visit(extractor)
    op = spec.paths["/user"].post
    assert op.parameters[0].schema_.type == "string"
