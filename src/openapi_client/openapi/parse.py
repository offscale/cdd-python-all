"""Module for parsing OpenAPI specifications."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from openapi_client.exceptions import ReferenceResolutionError, SpecificationParseError
from openapi_client.models import OpenAPI


def resolve_external_refs(
    obj: Any,
    base_path: Path = Path("."),
    visited: frozenset[Path] = frozenset(),
    allowed_root: Path | None = None,
) -> Any:
    """Recursively resolve cross-document `$ref` pointers safely within `allowed_root`.

    Args:
        obj: The JSON-compatible object (dict, list, or primitive) to resolve.
        base_path: Base directory path for resolving relative file references.
        visited: Set of already visited file paths to prevent infinite recursion.
        allowed_root: Optional root directory boundary that resolved paths must stay within.

    Returns:
        The resolved JSON structure with external references inlined where available.

    Raises:
        ReferenceResolutionError: If an external `$ref` escapes `allowed_root` or contains invalid JSON.
    """
    root_dir = (allowed_root or base_path).resolve()

    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            ref = obj["$ref"]
            if ref and not ref.startswith("#"):
                parts = ref.split("#", 1)
                file_path = parts[0]
                pointer = parts[1] if len(parts) > 1 else ""

                target_path = (base_path / file_path).resolve()
                if not target_path.is_relative_to(root_dir):
                    raise ReferenceResolutionError(
                        f"External $ref {ref!r} escapes allowed root {root_dir}"
                    )
                if target_path.is_file() and target_path not in visited:
                    raw_text = target_path.read_text(encoding="utf-8")
                    try:
                        content: Any = json.loads(raw_text)
                    except json.JSONDecodeError as err:
                        raise ReferenceResolutionError(
                            f"Invalid JSON in external $ref {ref!r}: {err}"
                        ) from err

                    valid_pointer = True
                    if pointer:
                        for part in pointer.strip("/").split("/"):
                            if part:
                                decoded_part = part.replace("~1", "/").replace(
                                    "~0", "~"
                                )
                                if not isinstance(content, dict):
                                    valid_pointer = False
                                    break
                                content = content.get(decoded_part, {})
                    if valid_pointer:
                        return resolve_external_refs(
                            content,
                            target_path.parent,
                            visited | {target_path},
                            root_dir,
                        )
        return {
            k: resolve_external_refs(v, base_path, visited, root_dir)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [
            resolve_external_refs(item, base_path, visited, root_dir) for item in obj
        ]
    return obj


def parse_openapi_dict(
    spec_dict: dict[str, Any], base_path: Path = Path(".")
) -> OpenAPI:
    """Parse an OpenAPI dictionary into an OpenAPI model without mutating the input dict.

    Args:
        spec_dict: Raw dictionary parsed from an OpenAPI or Swagger document.
        base_path: Base directory path for resolving external `$ref` files.

    Returns:
        The validated OpenAPI model instance.
    """
    isolated_dict = copy.deepcopy(spec_dict)
    resolved_dict = resolve_external_refs(isolated_dict, base_path)

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

    Raises:
        SpecificationParseError: If `spec_json` is not valid JSON.
    """
    try:
        spec_dict = json.loads(spec_json)
    except json.JSONDecodeError as err:
        raise SpecificationParseError(f"Invalid OpenAPI JSON: {err}") from err
    return parse_openapi_dict(spec_dict, base_path)
