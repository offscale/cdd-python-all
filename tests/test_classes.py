"""Tests for Pydantic model class emission and AST parsing."""

from __future__ import annotations

from unittest.mock import patch

import libcst as cst

from openapi_client.classes.emit import emit_classes, emit_models_module
from openapi_client.classes.parse import ClassExtractor, extract_classes_from_ast
from openapi_client.cli_sdk.emit import emit_cli
from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import (
    Components,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    Schema,
)


def test_classes_emit_branches() -> None:
    """Test emit_classes and emit_models_module with various property schemas."""
    assert emit_classes({}) == []

    schema = Schema(type="string")
    assert emit_classes({"test": schema}) == []

    schema_obj = Schema(
        type="object",
        required=["req_field"],
        properties={
            "req_field": Schema(type="string"),
            "opt_array": Schema(type="array"),
            "typed_array": Schema(type="array", items=Schema(type="integer")),
            "ref_field": Reference(**{"$ref": "#/components/schemas/Other"}),
            "bad_ref": Reference(**{"$ref": "invalid-ref"}),
            "list_type": Schema(type=["null", "integer"]),
            "all_null_list": Schema(type=["null"]),
        },
    )
    classes = emit_classes({"test_obj": schema_obj})
    assert len(classes) == 1
    code = emit_models_module({"test_obj": schema_obj})
    assert "req_field: str" in code
    assert "opt_array: list[Any] | None = None" in code
    assert "typed_array: list[int] | None = None" in code
    assert "ref_field: Other | None = None" in code
    assert "bad_ref: Any | None = None" in code


def test_classes_parse_branches() -> None:
    """Test ClassExtractor on union, optional, list, dict, and reference annotations."""
    code = """
class MyClass:
    def my_method(self):
        pass

    some_obj.attr: int

    prop1: Optional[1:2]
    prop2: Optional["string"]
    prop3: Optional[str]
    prop4: None | int = None
    prop5: int | str = 1
    prop6: list[str]
    prop7: dict[str, int]
    prop8: CustomModel
    prop9: float
    prop10: bool
"""
    module = cst.parse_module(code)
    spec = OpenAPI(
        openapi="3.1.0", info={"title": "Test", "version": "1.0.0"}, components=None
    )
    extract_classes_from_ast(module, spec)
    assert spec.components is not None
    assert spec.components.schemas is not None
    my_schema = spec.components.schemas["MyClass"]
    assert isinstance(my_schema, Schema)
    assert my_schema.properties is not None
    assert my_schema.properties["prop3"].type == "string"
    assert my_schema.properties["prop4"].type == "integer"
    assert my_schema.properties["prop6"].type == "array"
    assert my_schema.properties["prop7"].type == "object"
    assert isinstance(my_schema.properties["prop8"], Reference)
    assert my_schema.properties["prop9"].type == "number"
    assert my_schema.properties["prop10"].type == "boolean"
    assert "prop8" in (my_schema.required or [])


def test_classes_parse_schema_properties_none() -> None:
    """Test ClassExtractor when Schema.properties is None."""
    code = "class MyClass:\n    prop: int = 1\n"
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    visitor = ClassExtractor(spec)

    with patch("openapi_client.classes.parse.Schema") as mock_schema_cls:
        mock_schema_instance = mock_schema_cls.return_value
        mock_schema_instance.properties = None
        module.visit(visitor)
    assert spec.components is not None
    assert "MyClass" in (spec.components.schemas or {})


def test_classes_parse_components_none() -> None:
    """Test ClassExtractor when spec.components is set to None after init."""
    code = "class MyClass:\n    pass\n"
    module = cst.parse_module(code)
    spec = OpenAPI(
        openapi="3.1.0",
        info={"title": "Test", "version": "1.0.0"},
        components=Components(schemas=None),
    )
    visitor = ClassExtractor(spec)
    assert visitor.spec.components is not None
    assert visitor.spec.components.schemas == {}
    visitor.spec.components = None
    module.visit(visitor)
    assert visitor.spec.components is None


def test_cli_sdk_emit_branches() -> None:
    """Test emit_cli with empty and optional parameters."""
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    spec.paths = {
        "/test1": PathItem(
            get=Operation(
                operationId="test1",
                responses={},
                parameters=[],
            ),
            post=Operation(
                operationId="test2",
                responses={},
                parameters=[
                    Parameter(name="param1", **{"in": "query", "required": False})
                ],
            ),
        )
    }

    module = emit_cli(spec)
    assert "test1_parser" in module.code
    assert "test2_parser" in module.code


def test_docstring_empty_body():
    # 20->36
    """Test test_docstring_empty_body."""
    node = cst.FunctionDef(
        name=cst.Name("test"), params=cst.Parameters(), body=cst.IndentedBlock(body=[])
    )
    assert parse_docstring(node) == (None, None)


def test_docstring_empty_string():
    # 28->36
    """Test test_docstring_empty_string."""
    node = cst.FunctionDef(
        name=cst.Name("test"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString("''"))])
            ]
        ),
    )
    assert parse_docstring(node) == (None, None)
