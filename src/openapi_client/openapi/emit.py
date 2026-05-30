"""
Module for emitting OpenAPI specifications.
"""

from __future__ import annotations

import json
from typing import Any

from openapi_client.models import OpenAPI


def emit_openapi_dict(spec: OpenAPI) -> dict[str, Any]:
    """Emit an OpenAPI model as a dictionary."""
    if hasattr(spec, "model_dump"):
        return spec.model_dump(by_alias=True, exclude_none=True)
    return spec.dict(by_alias=True, exclude_none=True)  # pragma: no cover


def emit_openapi_json(spec: OpenAPI, indent: int = 2) -> str:
    """Emit an OpenAPI model as a JSON string."""
    spec_dict = emit_openapi_dict(spec)
    return json.dumps(spec_dict, indent=indent) + "\n"
