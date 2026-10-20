"""Module for extracting OpenAPI Schemas from Python class ASTs (Pydantic models)."""

from __future__ import annotations

import libcst as cst

from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import (
    Components,
    OpenAPI,
    Reference,
    Schema,
    SchemaOrReference,
)

_NON_MODEL_CLASS_NAMES = frozenset(
    {
        "Client",
        "Workflows",
        "StepError",
        "MCPAdapter",
        "DBConfig",
        "EntityPool",
        "CDDError",
    }
)

_NON_MODEL_BASE_NAMES = frozenset(
    {
        "Exception",
        "BaseException",
        "RuntimeError",
        "ValueError",
        "TypeError",
        "CSTVisitor",
        "ABC",
        "BaseHTTPRequestHandler",
    }
)


def _is_non_model_class(node: cst.ClassDef) -> bool:
    """Return True if `node` represents a non-schema class (e.g. client, workflow, exception, visitor).

    Args:
        node: The LibCST ClassDef node to inspect.

    Returns:
        `True` if the class should be skipped by `ClassExtractor`.
    """
    if node.name.value in _NON_MODEL_CLASS_NAMES:
        return True
    for base_arg in node.bases:
        expr = base_arg.value
        base_name = (
            expr.value
            if isinstance(expr, cst.Name)
            else (expr.attr.value if isinstance(expr, cst.Attribute) else "")
        )
        if base_name in _NON_MODEL_BASE_NAMES or base_name.endswith("Error"):
            return True
    return False


def _infer_schema_from_type_node(node: cst.BaseExpression) -> Schema | Reference:
    """Infer an OpenAPI Schema or Reference from a LibCST type annotation expression.

    Args:
        node: The LibCST expression representing a type annotation.

    Returns:
        The inferred OpenAPI Schema or Reference.
    """
    if isinstance(node, cst.BinaryOperation) and isinstance(node.operator, cst.BitOr):
        target_side = (
            node.right
            if isinstance(node.left, cst.Name) and node.left.value == "None"
            else node.left
        )
        return _infer_schema_from_type_node(target_side)

    if isinstance(node, cst.Name):
        val = node.value
        if val == "int":
            return Schema(type="integer")
        if val == "float":
            return Schema(type="number")
        if val == "bool":
            return Schema(type="boolean")
        if val in ("str", "Any"):
            return Schema(type="string")
        return Reference(**{"$ref": f"#/components/schemas/{val}"})

    if isinstance(node, cst.Subscript) and isinstance(node.value, cst.Name):
        base = node.value.value
        if (
            base in ("Optional", "Union")
            and node.slice
            and isinstance(node.slice[0].slice, cst.Index)
        ):
            return _infer_schema_from_type_node(node.slice[0].slice.value)
        if (
            base in ("list", "List")
            and node.slice
            and isinstance(node.slice[0].slice, cst.Index)
        ):
            item_schema = _infer_schema_from_type_node(node.slice[0].slice.value)
            return Schema(type="array", items=item_schema)
        if base in ("dict", "Dict"):
            return Schema(type="object")

    return Schema(type="string")


def _extract_field_call_metadata(call: cst.Call, schema: Schema) -> bool:
    """Populate `schema` constraints from a Pydantic `Field(...)` call and return whether required.

    Args:
        call: The `Field(...)` LibCST Call node.
        schema: The target OpenAPI Schema object to enrich.

    Returns:
        `True` if the `Field(...)` call marks the property as required (`...` or no default).
    """
    is_required = True
    for arg in call.args:
        kw = arg.keyword.value if arg.keyword else None
        val = arg.value
        if kw in (None, "default"):
            if isinstance(val, cst.Ellipsis):
                is_required = True
            else:
                is_required = False
                if isinstance(val, cst.SimpleString):
                    schema.default = val.evaluated_value
                elif isinstance(val, cst.Integer):
                    schema.default = int(val.value)
                elif isinstance(val, cst.Float):
                    schema.default = float(val.value)
        elif kw == "description" and isinstance(val, cst.SimpleString):
            schema.description = str(val.evaluated_value)
        elif kw == "ge" and isinstance(val, (cst.Integer, cst.Float)):
            schema.minimum = float(val.value)
        elif kw == "le" and isinstance(val, (cst.Integer, cst.Float)):
            schema.maximum = float(val.value)
        elif kw == "min_length" and isinstance(val, cst.Integer):
            schema.minLength = int(val.value)
        elif kw == "max_length" and isinstance(val, cst.Integer):
            schema.maxLength = int(val.value)
        elif kw == "pattern" and isinstance(val, cst.SimpleString):
            schema.pattern = str(val.evaluated_value)
    return is_required


class ClassExtractor(cst.CSTVisitor):
    """AST Visitor to extract Pydantic class definitions into OpenAPI Schemas."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize ClassExtractor with an OpenAPI spec.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec
        if self.spec.components is None:
            self.spec.components = Components(schemas={})
        if getattr(self.spec.components, "schemas", None) is None:
            self.spec.components.schemas = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Extract class structure to JSON Schema definitions inside components.schemas.

        Args:
            node: The LibCST ClassDef node being visited.
        """
        if _is_non_model_class(node):
            return

        name = node.name.value
        summary, description = parse_docstring(node)

        properties: dict[str, SchemaOrReference] = {}
        required_fields: list[str] = []

        if isinstance(node.body, cst.IndentedBlock):
            for statement in node.body.body:
                if isinstance(statement, cst.SimpleStatementLine):
                    for body_element in statement.body:
                        if isinstance(body_element, cst.AnnAssign):
                            target = body_element.target
                            if isinstance(target, cst.Name):
                                prop_name = target.value
                                ann_node = body_element.annotation.annotation
                                prop_schema = _infer_schema_from_type_node(ann_node)
                                is_nullable_union = (
                                    isinstance(ann_node, cst.BinaryOperation)
                                    and isinstance(ann_node.operator, cst.BitOr)
                                    and (
                                        (
                                            isinstance(ann_node.right, cst.Name)
                                            and ann_node.right.value == "None"
                                        )
                                        or (
                                            isinstance(ann_node.left, cst.Name)
                                            and ann_node.left.value == "None"
                                        )
                                    )
                                )
                                if (
                                    isinstance(body_element.value, cst.Call)
                                    and isinstance(body_element.value.func, cst.Name)
                                    and body_element.value.func.value == "Field"
                                    and isinstance(prop_schema, Schema)
                                ):
                                    field_req = _extract_field_call_metadata(
                                        body_element.value, prop_schema
                                    )
                                    if field_req and not is_nullable_union:
                                        required_fields.append(prop_name)
                                elif (
                                    body_element.value is None and not is_nullable_union
                                ):
                                    required_fields.append(prop_name)
                                properties[prop_name] = prop_schema

        schema = Schema(type="object", properties=properties)
        if summary:
            schema.summary = summary
        if description:
            schema.description = description
        if required_fields:
            schema.required = required_fields

        if self.spec.components is None or self.spec.components.schemas is None:
            self.spec.components = Components(schemas={})
        assert self.spec.components.schemas is not None
        self.spec.components.schemas[name] = schema


def extract_classes_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract API schemas from a parsed module into an OpenAPI specification.

    Args:
        module: Parsed Python module.
        spec: OpenAPI specification to update.
    """
    visitor = ClassExtractor(spec)
    module.visit(visitor)
