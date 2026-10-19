"""Module for parsing OpenAPI specifications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openapi_client.models import OpenAPI


def resolve_external_refs(
    obj: Any, base_path: Path = Path("."), visited: frozenset[Path] = frozenset()
) -> Any:
    """Recursively resolve cross-document `$ref` pointers.

    Args:
        obj: The JSON-compatible object (dict, list, or primitive) to resolve.
        base_path: Base directory path for resolving relative file references.
        visited: Set of already visited file paths to prevent infinite recursion.

    Returns:
        The resolved JSON structure with external references inlined where available.
    """
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            ref = obj["$ref"]
            if not ref.startswith("#"):
                parts = ref.split("#", 1)
                file_path = parts[0]
                pointer = parts[1] if len(parts) > 1 else ""

                try:
                    target_path = (base_path / file_path).resolve()
                    if target_path.exists() and target_path not in visited:
                        content: Any = json.loads(
                            target_path.read_text(encoding="utf-8")
                        )
                        if pointer:
                            for part in pointer.strip("/").split("/"):
                                if part:
                                    if not isinstance(content, dict):
                                        raise TypeError(
                                            f"Cannot traverse pointer {part!r} in non-dict"
                                        )
                                    content = content.get(part, {})
                        return resolve_external_refs(
                            content, target_path.parent, visited | {target_path}
                        )
                except (OSError, json.JSONDecodeError, TypeError, KeyError):
                    pass
        return {k: resolve_external_refs(v, base_path, visited) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_external_refs(item, base_path, visited) for item in obj]
    return obj


def parse_openapi_dict(
    spec_dict: dict[str, Any], base_path: Path = Path(".")
) -> OpenAPI:
    """Parse an OpenAPI dictionary into an OpenAPI model, resolving external refs.

    Args:
        spec_dict: Raw dictionary parsed from an OpenAPI or Swagger document.
        base_path: Base directory path for resolving external `$ref` files.

    Returns:
        The validated OpenAPI model instance.
    """
    resolved_dict = resolve_external_refs(spec_dict, base_path)

    components = resolved_dict.setdefault("components", {})
    if "definitions" in resolved_dict and "schemas" not in components:
        components["schemas"] = resolved_dict["definitions"]
    if "securityDefinitions" in resolved_dict and "securitySchemes" not in components:
        components["securitySchemes"] = resolved_dict["securityDefinitions"]
    if (
        "parameters" in resolved_dict
        and "parameters" not in components
        and isinstance(resolved_dict["parameters"], dict)
    ):
        components["parameters"] = resolved_dict["parameters"]
    if "responses" in resolved_dict and "responses" not in components:
        components["responses"] = resolved_dict["responses"]

    return OpenAPI(**resolved_dict)


def parse_openapi_json(spec_json: str, base_path: Path = Path(".")) -> OpenAPI:
    """Parse an OpenAPI JSON string into an OpenAPI model.

    Args:
        spec_json: Raw JSON string containing the OpenAPI specification.
        base_path: Base directory path for resolving external `$ref` files.

    Returns:
        The validated OpenAPI model instance.
    """
    spec_dict = json.loads(spec_json)
    return parse_openapi_dict(spec_dict, base_path)
