"""
Module for emitting Python classes (Pydantic models) from OpenAPI schemas.
"""

from typing import Dict, List, Optional, Union
import libcst as cst
from openapi_client.models import Schema, Reference, SchemaOrReference


def emit_class(name: str, schema: Schema) -> cst.ClassDef:
    """Emit a Pydantic BaseModel class from an OpenAPI Schema object."""
    class_body: List[cst.BaseStatement] = []

    from openapi_client.docstrings.emit import emit_class_docstring

    docstring = emit_class_docstring(schema)
    if docstring:
        class_body.append(docstring)

    if getattr(schema, "properties", None):
        for prop_name, prop_schema in schema.properties.items():  # type: ignore[union-attr]
            if isinstance(prop_schema, Reference):
                prop_type = "Any"  # Simplification for Reference
            else:
                prop_type = "Any"
                if getattr(prop_schema, "type", None) == "string":
                    prop_type = "str"
                elif getattr(prop_schema, "type", None) == "integer":
                    prop_type = "int"
                elif getattr(prop_schema, "type", None) == "number":
                    prop_type = "float"
                elif getattr(prop_schema, "type", None) == "boolean":
                    prop_type = "bool"

            class_body.append(
                cst.SimpleStatementLine(
                    [
                        cst.AnnAssign(
                            target=cst.Name(prop_name),
                            annotation=cst.Annotation(
                                cst.Subscript(
                                    value=cst.Name("Optional"),
                                    slice=[
                                        cst.SubscriptElement(
                                            cst.Index(cst.Name(prop_type))
                                        )
                                    ],
                                )
                            ),
                            value=cst.Name("None"),
                        )
                    ]
                )
            )

    if not class_body:
        class_body.append(cst.SimpleStatementLine([cst.Pass()]))

    return cst.ClassDef(
        name=cst.Name(name),
        bases=[cst.Arg(cst.Name("BaseModel"))],
        body=cst.IndentedBlock(body=class_body),  # type: ignore[arg-type]
    )


def emit_classes(schemas: Dict[str, SchemaOrReference]) -> List[cst.ClassDef]:
    """Emit a list of Pydantic BaseModel classes from a dictionary of OpenAPI Schema objects."""
    class_defs = []
    if schemas:
        for name, schema in schemas.items():
            if isinstance(schema, Schema) and getattr(schema, "type", None) == "object":
                class_defs.append(emit_class(name, schema))
    return class_defs
