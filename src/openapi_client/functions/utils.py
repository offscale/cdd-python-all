"""Utility functions for generating API client methods and mapping OpenAPI/Python types."""

from __future__ import annotations

import keyword
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import libcst as cst

if TYPE_CHECKING:  # pragma: no cover
    from openapi_client.models import OpenAPI, SchemaOrReference


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


def safe_param_name(raw_name: str) -> str:
    """Sanitize a parameter name while preserving valid camelCase identifiers.

    Args:
        raw_name: Raw parameter name from OpenAPI.

    Returns:
        A valid non-keyword Python identifier string.
    """
    if raw_name.isidentifier() and not keyword.iskeyword(raw_name):
        return raw_name
    return sanitize_name(raw_name)


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


def get_server_base_path(spec: OpenAPI | None, default_prefix: str = "/v2") -> str:
    """Extract the server `basePath` or first server URL path prefix from an OpenAPI spec.

    Args:
        spec: The OpenAPI specification model, if available.
        default_prefix: Default path prefix if neither `basePath` nor `servers` specifies a path.

    Returns:
        Normalized path prefix starting with `'/'` (e.g., `'/v2'` or `'/api/v3'`).
    """
    if spec is not None:
        base_path = getattr(spec, "basePath", None)
        if isinstance(base_path, str) and base_path.strip():
            norm = "/" + base_path.strip().lstrip("/")
            return norm.rstrip("/") or "/"
        servers = getattr(spec, "servers", None)
        if servers and len(servers) > 0:
            url = getattr(servers[0], "url", None)
            if isinstance(url, str) and url.strip():
                parsed_path = urlsplit(url.strip()).path
                if parsed_path and parsed_path != "/":
                    norm = "/" + parsed_path.lstrip("/")
                    return norm.rstrip("/")
    return default_prefix


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
    parsed_fallback = urlsplit(fallback)
    fallback_origin = (
        f"{parsed_fallback.scheme}://{parsed_fallback.netloc}"
        if parsed_fallback.scheme and parsed_fallback.netloc
        else "http://localhost:8080"
    )
    servers = getattr(spec, "servers", None) if spec is not None else None
    if servers and len(servers) > 0:
        url = getattr(servers[0], "url", None)
        if isinstance(url, str) and url.strip():
            raw_url = url.strip()
            if raw_url.startswith("/"):
                return f"{fallback_origin}{raw_url.rstrip('/')}"
            return raw_url
    base_path = getattr(spec, "basePath", None) if spec is not None else None
    if isinstance(base_path, str) and base_path.strip():
        norm_bp = "/" + base_path.strip().lstrip("/")
        return f"{fallback_origin}{norm_bp.rstrip('/')}"
    return fallback


def get_test_base_url(
    spec: OpenAPI | None,
    host: str = "http://localhost:8080",
    default_prefix: str = "/v2",
) -> str:
    """Resolve the default local integration test `API_URL` including the mounted `basePath`.

    Args:
        spec: The OpenAPI specification model, if available.
        host: Default local test server origin (scheme + host + port).
        default_prefix: Default path prefix if the spec has no `basePath` or server path.

    Returns:
        The local integration test URL including the OpenAPI base path prefix.
    """
    servers = getattr(spec, "servers", None) if spec is not None else None
    if servers and len(servers) > 0:
        url = getattr(servers[0], "url", None)
        if isinstance(url, str) and url.strip():
            parsed = urlsplit(url.strip())
            if parsed.hostname in ("localhost", "127.0.0.1"):
                return url.strip().rstrip("/")
    prefix = get_server_base_path(spec, default_prefix=default_prefix)
    if prefix == "/":
        return host.rstrip("/")
    return f"{host.rstrip('/')}{prefix}"


def build_cst_module(
    items: Sequence[cst.CSTNode],
) -> cst.Module:
    """Construct a strictly-typed `cst.Module` from statements and `cst.EmptyLine` separators.

    Args:
        items: Sequence of LibCST statements and optional `cst.EmptyLine` nodes.

    Returns:
        A `cst.Module` instance.
    """
    stmts: list[cst.SimpleStatementLine | cst.BaseCompoundStatement] = []
    pending_empty: list[cst.EmptyLine] = []
    for item in items:
        if isinstance(item, cst.EmptyLine):
            pending_empty.append(item)
        else:
            assert isinstance(
                item, (cst.SimpleStatementLine, cst.BaseCompoundStatement)
            )
            if pending_empty:
                existing = list(item.leading_lines)
                item = item.with_changes(leading_lines=[*existing, *pending_empty])
                pending_empty = []
            stmts.append(item)
    return cst.Module(body=stmts, footer=pending_empty)


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


def get_annotation_for_schema(
    s: SchemaOrReference | dict[str, Any] | None,
) -> str:
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
