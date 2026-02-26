import json
from typing import Dict, Any

from openapi_client.models import OpenAPI


def emit_openapi_dict(spec: OpenAPI) -> Dict[str, Any]:
    """Emit an OpenAPI model as a dictionary."""
    return spec.model_dump(by_alias=True, exclude_none=True)


def emit_openapi_json(spec: OpenAPI, indent: int = 2) -> str:
    """Emit an OpenAPI model as a JSON string."""
    spec_dict = emit_openapi_dict(spec)
    return json.dumps(spec_dict, indent=indent)
