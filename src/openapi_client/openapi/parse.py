import json
from typing import Dict, Any

from openapi_client.models import OpenAPI


def parse_openapi_dict(spec_dict: Dict[str, Any]) -> OpenAPI:
    """Parse an OpenAPI dictionary into an OpenAPI model."""
    return OpenAPI(**spec_dict)


def parse_openapi_json(spec_json: str) -> OpenAPI:
    """Parse an OpenAPI JSON string into an OpenAPI model."""
    spec_dict = json.loads(spec_json)
    return parse_openapi_dict(spec_dict)
