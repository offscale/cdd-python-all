"""
Utility functions for generating API client methods.
"""

import re


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def sanitize_name(name: str) -> str:
    """Sanitize a string to be a valid Python identifier in snake_case."""
    if not name:
        return ""
    sanitized = re.sub(r"\W|^(?=\d)", "_", name)
    return to_snake_case(sanitized)


def get_annotation_for_schema(s) -> str:
    """
    Get the Python type annotation string for a given OpenAPI Schema object.

    Args:
        s: The OpenAPI schema object.

    Returns:
        str: The Python type annotation as a string.
    """
    if not s:
        return "Any"
    t = getattr(s, "type", None)
    if t == "string":
        return "str"
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        items = getattr(s, "items", None)
        item_t = get_annotation_for_schema(items)
        return f"list[{item_t}]"
    if t == "object":
        return "dict[str, Any]"
    return "Any"
