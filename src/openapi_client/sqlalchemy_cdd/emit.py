"""Emit SQLAlchemy models using python-cdd."""

import ast
from collections import OrderedDict
from openapi_client.models import OpenAPI
from cdd.emit.sqlalchemy import sqlalchemy


def map_openapi_type_to_python(openapi_type: str) -> str:
    """Map OpenAPI type to Python type."""
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return type_map.get(openapi_type, "str")


def emit_sqlalchemy(spec: OpenAPI) -> str:
    """Generate SQLAlchemy models from OpenAPI using cdd."""
    if not spec.components or not spec.components.schemas:
        return ""

    body = [
        "from sqlalchemy.orm import declarative_base",
        "from sqlalchemy import Column, Integer, String, Float, Boolean, JSON",
        "",
        "Base = declarative_base()",
        "",
    ]

    for class_name, schema in spec.components.schemas.items():
        if hasattr(schema, "properties") and schema.properties:
            ir = {
                "name": class_name,
                "type": "static",
                "doc": getattr(schema, "description", "") or "",
                "params": OrderedDict(),
                "returns": None,
            }

            for prop_name, prop in schema.properties.items():
                p_type = getattr(prop, "type", "string")
                if isinstance(p_type, list):
                    p_type = p_type[0]

                doc = getattr(prop, "description", "") or ""
                # Make the first property the primary key if 'id' or we just pick the first one
                if prop_name.lower() == "id":
                    doc = f"[PK] {doc}".strip()

                ir["params"][prop_name] = {
                    "typ": map_openapi_type_to_python(p_type),
                    "doc": doc,
                    "default": None,
                }

            # Use cdd to generate the SQLAlchemy model AST
            sa_ast = sqlalchemy(
                ir,
                emit_repr=True,
                class_name=class_name,
                class_bases=("Base",),
                docstring_format="rest",
                word_wrap=True,
            )

            # Convert AST back to string
            try:
                code = ast.unparse(sa_ast)
                body.append(code)
                body.append("")
            except Exception as e:
                # Fallback if unparse fails (e.g. older python)
                pass

    return "\\n".join(body)
