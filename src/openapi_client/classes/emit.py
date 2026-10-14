"""Module for emitting Python classes (Pydantic models) from OpenAPI schemas."""

from __future__ import annotations

import libcst as cst

from openapi_client.docstrings.emit import emit_class_docstring
from openapi_client.models import Reference, Schema, SchemaOrReference


def _schema_to_type_annotation(prop_schema: SchemaOrReference) -> str:
    """Resolve a property Schema or Reference to a Python type expression string.

    Args:
        prop_schema: The property Schema or Reference object.

    Returns:
        A valid Python type expression string.
    """
    if isinstance(prop_schema, Reference):
        ref_str = getattr(prop_schema, "ref", "")
        if ref_str and "/" in ref_str:
            ref_name = ref_str.split("/")[-1]
            if ref_name.isidentifier():
                return ref_name
        return "Any"

    prop_type = getattr(prop_schema, "type", None)
    if isinstance(prop_type, list) and prop_type:
        non_null = [t for t in prop_type if t != "null"]
        prop_type = non_null[0] if non_null else prop_type[0]

    if prop_type == "string":
        return "str"
    if prop_type == "integer":
        return "int"
    if prop_type == "number":
        return "float"
    if prop_type == "boolean":
        return "bool"
    if prop_type == "array":
        items = getattr(prop_schema, "items", None)
        if isinstance(items, (Schema, Reference)):
            return f"list[{_schema_to_type_annotation(items)}]"
        return "list[Any]"
    if prop_type == "object":
        return "dict[str, Any]"
    return "Any"


def emit_class(name: str, schema: Schema) -> cst.ClassDef:
    """Emit a Pydantic BaseModel class from an OpenAPI Schema object.

    Args:
        name: The model class name.
        schema: The OpenAPI Schema definition.

    Returns:
        The generated LibCST ClassDef node.
    """
    class_body: list[cst.BaseStatement] = []

    docstring = emit_class_docstring(schema)
    if docstring:
        class_body.append(docstring)

    required_fields = set(getattr(schema, "required", None) or [])

    if schema.properties:
        for prop_name, prop_schema in schema.properties.items():
            prop_type = _schema_to_type_annotation(prop_schema)
            type_expr = cst.parse_expression(prop_type)

            if prop_name in required_fields:
                ann_expr = type_expr
                default_val: cst.BaseExpression | None = None
            else:
                ann_expr = cst.BinaryOperation(
                    left=type_expr,
                    operator=cst.BitOr(),
                    right=cst.Name("None"),
                )
                default_val = cst.Name("None")

            class_body.append(
                cst.SimpleStatementLine(
                    [
                        cst.AnnAssign(
                            target=cst.Name(prop_name),
                            annotation=cst.Annotation(ann_expr),
                            value=default_val,
                        )
                    ]
                )
            )

    if not class_body:
        class_body.append(cst.SimpleStatementLine([cst.Pass()]))

    return cst.ClassDef(
        name=cst.Name(name),
        bases=[cst.Arg(cst.Name("BaseModel"))],
        body=cst.IndentedBlock(body=class_body),
    )


def emit_classes(schemas: dict[str, SchemaOrReference]) -> list[cst.ClassDef]:
    """Emit a list of Pydantic BaseModel classes from a dictionary of OpenAPI Schema objects.

    Args:
        schemas: Mapping of schema names to Schema or Reference objects.

    Returns:
        List of generated LibCST ClassDef nodes.
    """
    class_defs: list[cst.ClassDef] = []
    if schemas:
        for name, schema in schemas.items():
            if isinstance(schema, Schema) and getattr(schema, "type", None) == "object":
                class_defs.append(emit_class(name, schema))
    return class_defs


def emit_models_module(schemas: dict[str, SchemaOrReference]) -> str:
    """Emit a complete Python module containing Pydantic models.

    Args:
        schemas: Mapping of schema names to Schema or Reference objects.

    Returns:
        The generated Python source code string for `models.py`.
    """
    body: list[cst.BaseStatement | cst.EmptyLine] = []

    body.append(
        cst.SimpleStatementLine(
            [
                cst.ImportFrom(
                    module=cst.Name("__future__"),
                    names=[
                        cst.ImportAlias(name=cst.Name("annotations")),
                    ],
                )
            ]
        )
    )
    body.append(
        cst.SimpleStatementLine(
            [
                cst.ImportFrom(
                    module=cst.Name("typing"),
                    names=[
                        cst.ImportAlias(name=cst.Name("Any")),
                    ],
                )
            ]
        )
    )
    body.append(
        cst.SimpleStatementLine(
            [
                cst.ImportFrom(
                    module=cst.Name("pydantic"),
                    names=[
                        cst.ImportAlias(name=cst.Name("BaseModel")),
                        cst.ImportAlias(name=cst.Name("Field")),
                    ],
                )
            ]
        )
    )
    body.append(cst.EmptyLine())

    class_defs = emit_classes(schemas)
    for class_def in class_defs:
        body.append(class_def)
        body.append(cst.EmptyLine())

    module = cst.Module(body=body)
    return module.code
