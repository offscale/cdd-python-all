"""Utility functions for generating API client methods and mapping OpenAPI/Python types."""

from __future__ import annotations

import keyword
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from openapi_client.models import OpenAPI


def to_snake_case(name: str) -> str:
    """Convert a string (e.g. camelCase or PascalCase) to snake_case.

    Args:
        name: The input string to convert.

    Returns:
        The snake_case representation of the string.
    """
    s1 = re.sub("([^_])([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def sanitize_name(name: str) -> str:
    """Sanitize a string to be a valid Python identifier in snake_case.

    Args:
        name: Raw name string (e.g. operationId, tag, or parameter name).

    Returns:
        A valid Python snake_case identifier.
    """
    if not name:
        return ""
    sanitized = re.sub(r"\W|^(?=\d)", "_", name)
    result = to_snake_case(sanitized)
    if keyword.iskeyword(result):
        return f"{result}_"
    return result


def sanitize_class_name(name: str) -> str:
    """Sanitize a schema name into a valid Python class identifier.

    Args:
        name: Raw schema name string (e.g. `'Pet-Input'` or `'User'`).

    Returns:
        A valid Python class identifier (e.g. `'PetInput'` or `'User'`).
    """
    if not name:
        return "Model"
    if name.isidentifier() and not keyword.iskeyword(name):
        return name
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", name) if p]
    if not parts:
        return "Model"
    result = "".join(p[0].upper() + p[1:] for p in parts)
    if result[0].isdigit():
        return f"_{result}"
    return result


def get_default_server_url(
    spec: OpenAPI | None, fallback: str = "http://localhost:8080/v2"
) -> str:
    """Resolve the default base URL from an OpenAPI specification.

    Args:
        spec: The OpenAPI specification model, if available.
        fallback: Fallback base URL if `spec.servers` is empty or missing.

    Returns:
        The resolved base URL string.
    """
    if spec is not None and getattr(spec, "servers", None) and len(spec.servers) > 0:
        url = getattr(spec.servers[0], "url", None)
        if url:
            return str(url)
    return fallback


def map_openapi_type_to_python(openapi_type: str) -> str:
    """Map an OpenAPI primitive type string to the corresponding Python built-in type string.

    Args:
        openapi_type: The OpenAPI type string (`'string'`, `'integer'`, `'number'`, `'boolean'`, `'array'`, `'object'`).

    Returns:
        The corresponding Python type string (`'str'`, `'int'`, `'float'`, `'bool'`, `'list'`, `'dict'`).
    """
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return type_map.get(openapi_type, "str")


def get_annotation_for_schema(s: Any) -> str:
    """Get the Python type annotation string for a given OpenAPI Schema or Reference object.

    Args:
        s: The OpenAPI schema, reference, or dictionary object.

    Returns:
        The Python type annotation as a string.
    """
    if not s:
        return "Any"
    ref_str = s.get("$ref") if isinstance(s, dict) else getattr(s, "ref", None)
    if isinstance(ref_str, str) and "/" in ref_str:
        ref_name = ref_str.split("/")[-1]
        if ref_name.isidentifier():
            return ref_name
    t = s.get("type") if isinstance(s, dict) else getattr(s, "type", None)
    if isinstance(t, list) and t:
        non_null = [item for item in t if item != "null"]
        t = non_null[0] if non_null else t[0]
    if t == "string":
        return "str"
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        items = s.get("items") if isinstance(s, dict) else getattr(s, "items", None)
        item_t = get_annotation_for_schema(items)
        return f"list[{item_t}]"
    if t == "object":
        return "dict[str, Any]"
    return "Any"
