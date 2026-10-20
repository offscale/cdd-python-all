"""Mock test client."""

from __future__ import annotations

import libcst as cst

from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import Info, OpenAPI


def test_client() -> None:
    """Verify the mock server module parses cleanly into an OpenAPI specification."""
    with open("test/mock_server.py", encoding="utf-8") as f:
        code = f.read()
    spec = OpenAPI(openapi="3.2.0", info=Info(title="Mock", version="1.0.0"), paths={})
    extract_mocks_from_ast(cst.parse_module(code), spec)
    assert spec.openapi == "3.2.0"
