"""Module for extracting OpenAPI Schemas from Python class ASTs (Pydantic models)."""

from __future__ import annotations

import libcst as cst

from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import Components, OpenAPI, Reference, Schema


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
        name = node.name.value
        if name == "Client":
            return

        summary, description = parse_docstring(node)

        schema = Schema(type="object", properties={})
        if summary:
            schema.summary = summary
        if description:
            schema.description = description

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
                                if body_element.value is None and not is_nullable_union:
                                    required_fields.append(prop_name)
                                if schema.properties is not None:
                                    schema.properties[prop_name] = prop_schema

        if required_fields:
            schema.required = required_fields

        if self.spec.components and self.spec.components.schemas is not None:
            self.spec.components.schemas[name] = schema


def extract_classes_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract API schemas from a parsed module into an OpenAPI specification.

    Args:
        module: Parsed Python module.
        spec: OpenAPI specification to update.
    """
    visitor = ClassExtractor(spec)
    module.visit(visitor)
