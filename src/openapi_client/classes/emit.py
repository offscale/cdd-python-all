"""Module for emitting Python classes (Pydantic models) from OpenAPI schemas."""

from __future__ import annotations

from collections.abc import Mapping

import libcst as cst

from openapi_client.docstrings.emit import emit_class_docstring
from openapi_client.functions.utils import build_cst_module, get_annotation_for_schema
from openapi_client.models import Schema, SchemaOrReference


def _schema_to_type_annotation(prop_schema: SchemaOrReference) -> str:
    """Resolve a property Schema or Reference to a Python type expression string.

    Args:
        prop_schema: The property Schema or Reference object.

    Returns:
        A valid Python type expression string.
    """
    return get_annotation_for_schema(prop_schema)


def _build_field_default(
    prop_schema: SchemaOrReference, is_required: bool
) -> cst.BaseExpression | None:
    """Build a default value or `Field(...)` call when schema constraints/metadata exist.

    Args:
        prop_schema: The property Schema or Reference object.
        is_required: Whether the property is in the parent schema's `required` list.

    Returns:
        A LibCST expression for the field default/Field(...) or `None` if required without metadata.
    """
    if isinstance(prop_schema, Schema):
        field_kwargs: list[str] = []
        if prop_schema.default is not None:
            field_kwargs.append(f"default={prop_schema.default!r}")
        elif not is_required:
            field_kwargs.append("default=None")
        else:
            field_kwargs.append("default=...")

        has_meta = False
        if prop_schema.description:
            field_kwargs.append(f"description={prop_schema.description!r}")
            has_meta = True
        if prop_schema.minimum is not None:
            field_kwargs.append(f"ge={prop_schema.minimum!r}")
            has_meta = True
        if prop_schema.maximum is not None:
            field_kwargs.append(f"le={prop_schema.maximum!r}")
            has_meta = True
        if prop_schema.minLength is not None:
            field_kwargs.append(f"min_length={prop_schema.minLength!r}")
            has_meta = True
        if prop_schema.maxLength is not None:
            field_kwargs.append(f"max_length={prop_schema.maxLength!r}")
            has_meta = True
        if prop_schema.pattern is not None:
            field_kwargs.append(f"pattern={prop_schema.pattern!r}")
            has_meta = True
        if prop_schema.default is not None:
            has_meta = True

        if has_meta:
            return cst.parse_expression(f"Field({', '.join(field_kwargs)})")

    return None if is_required else cst.Name("None")


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
            is_req = prop_name in required_fields

            if is_req:
                ann_expr = type_expr
            else:
                ann_expr = cst.BinaryOperation(
                    left=type_expr,
                    operator=cst.BitOr(),
                    right=cst.Name("None"),
                )

            default_val = _build_field_default(prop_schema, is_req)

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


def emit_classes(schemas: Mapping[str, SchemaOrReference]) -> list[cst.ClassDef]:
    """Emit a list of Pydantic BaseModel classes from a dictionary of OpenAPI Schema objects.

    Args:
        schemas: Mapping of schema names to Schema or Reference objects.

    Returns:
        List of generated LibCST ClassDef nodes.
    """
    class_defs: list[cst.ClassDef] = []
    if schemas:
        for name, schema in schemas.items():
            if isinstance(schema, Schema) and (
                getattr(schema, "type", None) == "object"
                or getattr(schema, "properties", None) is not None
            ):
                class_defs.append(emit_class(name, schema))
    return class_defs


def emit_models_module(schemas: Mapping[str, SchemaOrReference]) -> str:
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

    module = build_cst_module(body)
    return module.code
