"""Module for emitting Arazzo 1.1.0 specifications to dictionaries and JSON."""

from __future__ import annotations

import json
from typing import Any

from openapi_client.arazzo_models import Arazzo


def emit_arazzo_dict(spec: Arazzo) -> dict[str, Any]:
    """Emit an `Arazzo` specification model as a dictionary.

    Args:
        spec: The `Arazzo` model instance.

    Returns:
        The serialized Arazzo dictionary with `None` fields omitted and field aliases applied.
    """
    return spec.model_dump(by_alias=True, exclude_none=True)


def emit_arazzo_json(spec: Arazzo, indent: int = 2) -> str:
    """Emit an `Arazzo` specification model as a formatted JSON string.

    Args:
        spec: The `Arazzo` model instance.
        indent: JSON indentation spaces (defaults to 2).

    Returns:
        The formatted JSON string ending with a newline.
    """
    spec_dict = emit_arazzo_dict(spec)
    return json.dumps(spec_dict, indent=indent) + chr(10)
