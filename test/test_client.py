"""Mock test client."""

from __future__ import annotations

import libcst as cst

from openapi_client.mocks.parse import extract_mocks_from_ast
from openapi_client.models import Info, MediaType, OpenAPI, Response


def test_client() -> None:
    """Verify the mock server module parses into an OpenAPI specification with routes and SSE."""
    with open("test/mock_server.py", encoding="utf-8") as f:
        code = f.read()
    spec = OpenAPI(openapi="3.2.0", info=Info(title="Mock", version="1.0.0"), paths={})
    extract_mocks_from_ast(cst.parse_module(code), spec)
    assert spec.paths is not None
    assert "/pets" in spec.paths
    pets_get = spec.paths["/pets"].get
    assert pets_get is not None
    assert pets_get.operationId == "list_pets"
    assert pets_get.summary == "List all pets."
    assert pets_get.description == "Returns all pets registered in the mock store."

    assert "/pets/events" in spec.paths
    events_get = spec.paths["/pets/events"].get
    assert events_get is not None
    assert events_get.operationId == "stream_pet_events"
    assert events_get.responses is not None
    resp_200 = events_get.responses["200"]
    assert isinstance(resp_200, Response)
    assert resp_200.content is not None
    assert isinstance(resp_200.content["text/event-stream"], MediaType)
