"""Utility functions for generating API client methods."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from openapi_client.models import OpenAPI


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case.

    Args:
        name: The identifier string to convert.

    Returns:
        The snake_case representation of the identifier.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
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
    return to_snake_case(sanitized)


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


def get_annotation_for_schema(s: Any) -> str:
    """Get the Python type annotation string for a given OpenAPI Schema object.

    Args:
        s: The OpenAPI schema or reference object.

    Returns:
        The Python type annotation as a string.
    """
    if not s:
        return "Any"
    t = getattr(s, "type", None)
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
        items = getattr(s, "items", None)
        item_t = get_annotation_for_schema(items)
        return f"list[{item_t}]"
    if t == "object":
        return "dict[str, Any]"
    return "Any"
