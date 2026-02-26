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
