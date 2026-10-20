"""Mock server."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

app = FastAPI()


def EventSourceResponse(content: Any) -> Any:
    """Stub SSE response wrapper for mock server endpoints.

    Args:
        content: Event stream payload or generator.

    Returns:
        The wrapped event stream response payload.
    """
    return content


@app.get("/pets")
def list_pets() -> list[dict[str, Any]]:
    """List all pets.

    Returns all pets registered in the mock store.
    """
    return [{"id": 1, "name": "Rex"}]


@app.get("/pets/events")
def stream_pet_events() -> Any:
    """Stream pet events over Server-Sent Events."""
    return EventSourceResponse("data: ok\n\n")
