"""SQLAlchemy CDD code parsing module."""

from __future__ import annotations

import libcst as cst

from openapi_client.classes.parse import _is_non_model_class, extract_classes_from_ast
from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import Components, OpenAPI, Schema, SchemaOrReference

_SA_TYPE_MAP: dict[str, str] = {
    "Integer": "integer",
    "BigInteger": "integer",
    "SmallInteger": "integer",
    "Float": "number",
    "Numeric": "number",
    "Boolean": "boolean",
    "JSON": "object",
    "String": "string",
    "Text": "string",
}


def extract_sqlalchemy_column(call: cst.Call) -> tuple[Schema, bool]:
    """Extract an OpenAPI `Schema` and `is_required` flag from a SQLAlchemy `Column(...)` call.

    Args:
        call: The LibCST `Call` node representing `Column(...)` or `mapped_column(...)`.

    Returns:
        A tuple of `(schema, is_required)`.
    """
    col_type = "string"
    description: str | None = None
    is_required = False
    default_val: str | int | float | bool | None = None

    for arg in call.args:
        kw = arg.keyword.value if arg.keyword else None
        val = arg.value
        if kw is None:
            type_name = ""
            if isinstance(val, cst.Name):
                type_name = val.value
            elif isinstance(val, cst.Call):
                type_name = getattr(val.func, "value", "")
            if type_name in _SA_TYPE_MAP:
                col_type = _SA_TYPE_MAP[type_name]
        elif kw in ("doc", "comment") and isinstance(val, cst.SimpleString):
            raw_doc = str(val.evaluated_value)
            if raw_doc.startswith("[PK]"):
                is_required = True
                raw_doc = raw_doc[4:].strip()
            if raw_doc:
                description = raw_doc
        elif kw == "primary_key" and isinstance(val, cst.Name):
            if val.value == "True":
                is_required = True
        elif kw == "nullable" and isinstance(val, cst.Name):
            if val.value == "False":
                is_required = True
        elif kw == "default":
            if isinstance(val, cst.SimpleString):
                default_val = str(val.evaluated_value)
            elif isinstance(val, cst.Integer):
                default_val = int(val.value)
            elif isinstance(val, cst.Float):
                default_val = float(val.value)
            elif isinstance(val, cst.Name) and val.value in ("True", "False"):
                default_val = val.value == "True"

    schema = Schema(type=col_type)
    if description:
        schema.description = description
    if default_val is not None:
        schema.default = default_val
    return schema, is_required


class SQLAlchemyExtractor(cst.CSTVisitor):
    """AST Visitor to extract SQLAlchemy declarative models into OpenAPI Schemas."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize SQLAlchemyExtractor with an OpenAPI specification.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Extract SQLAlchemy `Column(...)` assignments from a model class definition.

        Args:
            node: The LibCST `ClassDef` node being visited.
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
                        if (
                            isinstance(body_element, cst.Assign)
                            and isinstance(body_element.value, cst.Call)
                            and isinstance(body_element.value.func, cst.Name)
                            and body_element.value.func.value
                            in ("Column", "mapped_column")
                        ):
                            for assign_target in body_element.targets:
                                col_name = getattr(assign_target.target, "value", None)
                                if isinstance(col_name, str) and col_name:
                                    col_schema, is_req = extract_sqlalchemy_column(
                                        body_element.value
                                    )
                                    properties[col_name] = col_schema
                                    if is_req and col_name not in required_fields:
                                        required_fields.append(col_name)

        if not properties:
            return

        schema = Schema(type="object", properties=properties)
        if summary:
            schema.summary = summary
        if description:
            schema.description = description
        if required_fields:
            schema.required = required_fields

        if self.spec.components is None:
            self.spec.components = Components(schemas={})
        if self.spec.components.schemas is None:
            self.spec.components.schemas = {}
        self.spec.components.schemas[name] = schema


def parse_sqlalchemy_cdd(module: cst.Module, spec: OpenAPI) -> None:
    """Parse SQLAlchemy CDD code into OpenAPI component schemas.

    Args:
        module: The parsed LibCST Module node.
        spec: The OpenAPI specification to update.
    """
    extract_classes_from_ast(module, spec)
    visitor = SQLAlchemyExtractor(spec)
    module.visit(visitor)
