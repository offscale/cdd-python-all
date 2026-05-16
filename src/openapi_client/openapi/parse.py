"""
Module for parsing OpenAPI specifications.
"""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path

from openapi_client.models import OpenAPI


def resolve_external_refs(obj: Any, base_path: Path = Path(".")) -> Any:
    """Recursively resolve cross-document `$ref` pointers."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref = obj["$ref"]
            if not ref.startswith("#"):
                # External reference
                parts = ref.split("#", 1)
                file_path = parts[0]
                pointer = parts[1] if len(parts) > 1 else ""

                # Check if it is a local file
                try:
                    target_path = base_path / file_path
                    if target_path.exists():
                        content = json.loads(target_path.read_text(encoding="utf-8"))
                        if pointer:
                            for part in pointer.strip("/").split("/"):
                                if part:
                                    content = content.get(part, {})
                        return resolve_external_refs(content, target_path.parent)
                except Exception:
                    pass
        return {k: resolve_external_refs(v, base_path) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_external_refs(item, base_path) for item in obj]
    return obj


def parse_openapi_dict(
    spec_dict: dict[str, Any], base_path: Path = Path(".")
) -> OpenAPI:
    """Parse an OpenAPI dictionary into an OpenAPI model, resolving external refs."""
    spec_dict = resolve_external_refs(spec_dict, base_path)

    components = spec_dict.setdefault("components", {})
    if "definitions" in spec_dict and "schemas" not in components:
        components["schemas"] = spec_dict["definitions"]
    if "securityDefinitions" in spec_dict and "securitySchemes" not in components:
        components["securitySchemes"] = spec_dict["securityDefinitions"]
    if "parameters" in spec_dict and "parameters" not in components:
        if isinstance(spec_dict["parameters"], dict):
            components["parameters"] = spec_dict["parameters"]
    if "responses" in spec_dict and "responses" not in components:
        components["responses"] = spec_dict["responses"]

    return OpenAPI(**spec_dict)


def parse_openapi_json(spec_json: str, base_path: Path = Path(".")) -> OpenAPI:
    """Parse an OpenAPI JSON string into an OpenAPI model."""
    spec_dict = json.loads(spec_json)
    return parse_openapi_dict(spec_dict, base_path)
