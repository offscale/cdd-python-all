"""Tests for Pydantic model class emission and AST parsing."""

from __future__ import annotations

from typing import Any

import libcst as cst
import pytest
from pydantic import ValidationError

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


def test_classes_emit_and_execute_generated_models() -> None:
    """Test emit_classes and emit_models_module, compiling and instantiating the generated Pydantic models."""
    assert emit_classes({}) == []

    schema = Schema(type="string")
    assert emit_classes({"test": schema}) == []

    other_schema = Schema(
        type="object",
        required=["id"],
        properties={
            "id": Schema(
                type="integer",
                description="Unique identifier",
                minimum=1,
                maximum=1000,
            ),
            "tag": Schema(
                type="string",
                default="general",
                minLength=2,
                maxLength=20,
                pattern="^[a-z]+$",
            ),
            "weight": Schema(type="number", default=1.5),
            "count": Schema(type="integer", default=0),
            "notes": Schema(type="string", description="Optional notes"),
        },
    )

    schema_obj = Schema(
        type="object",
        required=["req_field"],
        properties={
            "req_field": Schema(type="string", description="Required name"),
            "opt_array": Schema(type="array"),
            "typed_array": Schema(type="array", items=Schema(type="integer")),
            "ref_field": Reference(**{"$ref": "#/components/schemas/Other"}),
            "bad_ref": Reference(**{"$ref": "invalid-ref"}),
            "list_type": Schema(type=["null", "integer"]),
            "all_null_list": Schema(type=["null"]),
        },
    )
    schemas_map = {"Other": other_schema, "TestObj": schema_obj}
    classes = emit_classes(schemas_map)
    assert len(classes) == 2
    code = emit_models_module(schemas_map)
    assert "req_field: str = Field(default=..., description='Required name')" in code
    assert "opt_array: list[Any] | None = None" in code
    assert "typed_array: list[int] | None = None" in code
    assert "ref_field: Other | None = None" in code
    assert "bad_ref: Any | None = None" in code

    # Compile and execute generated models.py and instantiate the Pydantic models
    compiled = compile(code, "<models>", "exec")
    ns: dict[str, Any] = {}
    exec(compiled, ns)  # noqa: S102

    other_cls = ns["Other"]
    test_obj_cls = ns["TestObj"]
    other_cls.model_rebuild(_types_namespace=ns)
    test_obj_cls.model_rebuild(_types_namespace=ns)

    other_inst = other_cls(id=5)
    assert other_inst.id == 5
    assert other_inst.tag == "general"
    assert other_inst.weight == 1.5
    assert other_inst.count == 0

    with pytest.raises(ValidationError):
        other_cls(id=0)  # violates ge=1

    test_inst = test_obj_cls(
        req_field="hello", typed_array=[1, 2, 3], ref_field=other_inst
    )
    assert test_inst.req_field == "hello"
    assert test_inst.typed_array == [1, 2, 3]
    assert test_inst.ref_field.id == 5

    # Round-trip AST extraction of the generated models.py (including Field(...) metadata)
    rt_spec = OpenAPI(
        openapi="3.2.0", info={"title": "Test", "version": "1.0.0"}, components=None
    )
    extract_classes_from_ast(cst.parse_module(code), rt_spec)
    assert rt_spec.components is not None
    assert rt_spec.components.schemas is not None
    extracted_other = rt_spec.components.schemas["Other"]
    assert isinstance(extracted_other, Schema)
    assert extracted_other.properties is not None
    id_prop = extracted_other.properties["id"]
    assert isinstance(id_prop, Schema)
    assert id_prop.description == "Unique identifier"
    assert id_prop.minimum == 1.0
    assert id_prop.maximum == 1000.0
    tag_prop = extracted_other.properties["tag"]
    assert isinstance(tag_prop, Schema)
    assert tag_prop.default == "general"
    assert tag_prop.minLength == 2
    assert tag_prop.maxLength == 20
    assert tag_prop.pattern == "^[a-z]+$"


def test_classes_parse_branches() -> None:
    """Test ClassExtractor on union, optional, list, dict, reference annotations, and non-model filtering."""
    code = """
from pydantic import BaseModel, Field

class Workflows:
    pass

class CustomError(Exception):
    pass

class MyVisitor(cst.CSTVisitor):
    pass

class MyClass(BaseModel):
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
    prop11: str = Field("pos_default", unknown_kw=123)
"""
    module = cst.parse_module(code)
    spec = OpenAPI(
        openapi="3.1.0", info={"title": "Test", "version": "1.0.0"}, components=None
    )
    extract_classes_from_ast(module, spec)
    assert spec.components is not None
    assert spec.components.schemas is not None
    assert "Workflows" not in spec.components.schemas
    assert "CustomError" not in spec.components.schemas
    assert "MyVisitor" not in spec.components.schemas
    my_schema = spec.components.schemas["MyClass"]
    assert isinstance(my_schema, Schema)
    assert my_schema.properties is not None
    assert getattr(my_schema.properties["prop3"], "type", None) == "string"
    assert getattr(my_schema.properties["prop4"], "type", None) == "integer"
    assert getattr(my_schema.properties["prop6"], "type", None) == "array"
    assert getattr(my_schema.properties["prop7"], "type", None) == "object"
    assert isinstance(my_schema.properties["prop8"], Reference)
    assert getattr(my_schema.properties["prop9"], "type", None) == "number"
    assert getattr(my_schema.properties["prop10"], "type", None) == "boolean"
    assert getattr(my_schema.properties["prop11"], "default", None) == "pos_default"
    assert "prop8" in (my_schema.required or [])


def test_classes_parse_reinitializes_cleared_components() -> None:
    """Test ClassExtractor reinitializes components and schemas if cleared before visiting."""
    code = """class MyClass:
    prop: int = 1
"""
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
    assert visitor.spec.components is not None
    assert "MyClass" in (visitor.spec.components.schemas or {})


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


def test_docstring_empty_body() -> None:
    """Test parse_docstring with an empty function body."""
    node = cst.FunctionDef(
        name=cst.Name("test"), params=cst.Parameters(), body=cst.IndentedBlock(body=[])
    )
    assert parse_docstring(node) == (None, None)


def test_docstring_empty_string() -> None:
    """Test parse_docstring with an empty string literal."""
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
