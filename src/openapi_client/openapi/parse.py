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

                # Check if it's a local file
                try:
                    target_path = base_path / file_path
                    if target_path.exists():
                        content = json.loads(target_path.read_text(encoding="utf-8"))
                        if pointer:
                            for part in pointer.strip("/").split("/"):
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
    if "definitions" in spec_dict and "components" not in spec_dict:
        spec_dict["components"] = {"schemas": spec_dict["definitions"]}
    elif "definitions" in spec_dict and "schemas" not in spec_dict.get("components", {}):
        spec_dict.setdefault("components", {})["schemas"] = spec_dict["definitions"]
    return OpenAPI(**spec_dict)


def parse_openapi_json(spec_json: str, base_path: Path = Path(".")) -> OpenAPI:
    """Parse an OpenAPI JSON string into an OpenAPI model."""
    spec_dict = json.loads(spec_json)
    return parse_openapi_dict(spec_dict, base_path)
