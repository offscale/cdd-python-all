"""Emit SQLAlchemy models using python-cdd."""

from __future__ import annotations

import ast
from collections import OrderedDict
from typing import Any

from cdd.emit.sqlalchemy import sqlalchemy

from openapi_client.functions.utils import map_openapi_type_to_python, sanitize_name
from openapi_client.models import OpenAPI


def emit_sqlalchemy(spec: OpenAPI) -> dict[str, str]:
    """Generate SQLAlchemy models from OpenAPI using python-cdd in a modular way.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        A dictionary mapping relative model file paths to generated Python code.
    """
    if not spec.components or not spec.components.schemas:
        return {}

    files: dict[str, str] = {}
    init_body = [
        "from sqlalchemy.orm import declarative_base",
        "",
        "Base = declarative_base()",
        "",
    ]

    for class_name, schema in spec.components.schemas.items():
        if hasattr(schema, "properties") and schema.properties:
            params: OrderedDict[str, dict[str, Any]] = OrderedDict()
            ir: dict[str, Any] = {
                "name": class_name,
                "type": "static",
                "doc": getattr(schema, "description", "") or "",
                "params": params,
                "returns": None,
            }

            for prop_name, prop in schema.properties.items():
                p_type = getattr(prop, "type", "string")
                if isinstance(p_type, list):
                    p_type = p_type[0]

                doc = getattr(prop, "description", "") or ""
                if prop_name.lower() == "id":
                    doc = f"[PK] {doc}".strip()

                mapped_type = map_openapi_type_to_python(str(p_type))
                params[prop_name] = {
                    "typ": "dict" if mapped_type == "list" else mapped_type,
                    "doc": doc,
                    "default": None,
                }

            sa_ast = sqlalchemy(
                ir,
                emit_repr=True,
                class_name=class_name,
                class_bases=("Base",),
                docstring_format="rest",
                word_wrap=True,
            )

            code = ast.unparse(sa_ast)
            model_code = [
                "from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, Identity",
                "from . import Base",
                "",
                code,
                "",
            ]
            module_stem = sanitize_name(class_name) or class_name.lower()
            filename = f"models/{module_stem}.py"
            files[filename] = "\n".join(model_code)

            init_body.append(f"from .{module_stem} import {class_name}")

    files["models/__init__.py"] = "\n".join(init_body)

    return files


emit_sqlalchemy_cdd = emit_sqlalchemy
