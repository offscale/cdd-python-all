"""Module for emitting OpenAPI specifications."""

from __future__ import annotations

import json
from typing import Any

from openapi_client.models import OpenAPI


def emit_openapi_dict(spec: OpenAPI) -> dict[str, Any]:
    """Emit an OpenAPI model as a dictionary.

    Args:
        spec: The OpenAPI model instance.

    Returns:
        The serialized OpenAPI dictionary with `None` fields excluded.
    """
    return spec.model_dump(by_alias=True, exclude_none=True)


def emit_openapi_json(spec: OpenAPI, indent: int = 2) -> str:
    """Emit an OpenAPI model as a JSON string.

    Args:
        spec: The OpenAPI model instance.
        indent: JSON indentation spaces (defaults to 2).

    Returns:
        The formatted JSON string ending with a newline.
    """
    spec_dict = emit_openapi_dict(spec)
    return json.dumps(spec_dict, indent=indent) + "\n"
