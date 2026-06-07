"""Tests for test_coverage_more_branches.py."""

import libcst as cst
from unittest.mock import patch
from openapi_client.classes.parse import ClassExtractor, extract_classes_from_ast
from openapi_client.models import OpenAPI
from openapi_client.cli_sdk.emit import emit_cli
from openapi_client.models import PathItem, Operation, Parameter

from openapi_client.classes.emit import emit_classes
from openapi_client.models import Schema


def test_classes_emit_branches():
    # 67->71: empty schemas
    """Test test_classes_emit_branches."""
    emit_classes({})

    # 69->68: non-object schema
    schema = Schema(type="string")
    emit_classes({"test": schema})

    schema_obj = Schema(type="object", properties={"test_prop": Schema(type="array")})
    emit_classes({"test_obj": schema_obj})


def test_classes_parse_branches():
    """Test test_classes_parse_branches."""
    # We will construct a cst.Module with various class definitions to hit the branches.
    """Test test_classes_parse_branches."""
    code = """
class MyClass:
    # 45->44: statement is not SimpleStatementLine (it's a FunctionDef)
    def my_method(self):
        pass

    # 49->46: target is not Name (it's Attribute)
    some_obj.attr: int

    # 60->71: slice_elements[0].slice is not Index (it's Slice)
    prop1: Optional[1:2]

    # 64->71: index_val is not Name (it's SimpleString)
    prop2: Optional["string"]

    # normal Optional
    prop3: Optional[str]
"""
    module = cst.parse_module(code)
    spec = OpenAPI(
        openapi="3.1.0", info={"title": "Test", "version": "1.0.0"}, components=None
    )
    extract_classes_from_ast(module, spec)


def test_classes_parse_schema_properties_none():
    """Test test_classes_parse_schema_properties_none."""
    code = "class MyClass:\n    prop: int\n"
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    visitor = ClassExtractor(spec)
    # mock schema.properties to be None during the loop
    from unittest.mock import patch

    with patch("openapi_client.classes.parse.Schema") as mock_schema_cls:
        mock_schema_instance = mock_schema_cls.return_value
        mock_schema_instance.properties = None
        module.visit(visitor)


def test_classes_parse_components_none():
    """Test test_classes_parse_components_none."""
    code = "class MyClass:\n    pass\n"
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    visitor = ClassExtractor(spec)
    visitor.spec.components = None  # set it to None to hit 76->exit
    module.visit(visitor)


class MockSchemaForProperties:
    """Test MockSchemaForProperties."""

    def __init__(self, **kwargs):
        """Test __init__."""
        self._properties = None

    @property
    def properties(self):
        """Test properties."""
        return self._properties

    @properties.setter
    def properties(self, value):
        # ignore assignment
        """Test properties."""
        pass


def test_classes_parse_schema_properties_none_fix():
    """Test test_classes_parse_schema_properties_none_fix."""
    code = "class MyClass:\n    prop: int\n"
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})
    visitor = ClassExtractor(spec)
    with patch("openapi_client.classes.parse.Schema", MockSchemaForProperties):
        module.visit(visitor)


def test_cli_sdk_emit_branches():
    """Test test_cli_sdk_emit_branches."""
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})

    # Path with an operation that has NO parameters (hits 127->85)
    # And another operation that HAS parameters, but not required (hits 143->152)
    spec.paths = {
        "/test1": PathItem(
            get=Operation(
                operationId="test1",
                responses={},
                parameters=[],  # empty parameters
            ),
            post=Operation(
                operationId="test2",
                responses={},
                parameters=[
                    Parameter(name="param1", **{"in": "query", "required": False})
                ],  # not required
            ),
        )
    }

    module = emit_cli(spec)
    assert module is not None
