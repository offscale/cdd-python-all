"""Test for README generation."""

from openapi_client.fastapi.emit_readme import emit_readme
from openapi_client.models import OpenAPI


def test_emit_readme():
    """Test emit_readme with empty spec."""
    spec = OpenAPI(info={"title": "Test Title", "version": "1.0"}, openapi="3.2.0")
    code = emit_readme(spec)

    assert "# Test Title" in code
    assert "### 1. Stub Mode" in code
    assert "### 4. Full Mock Mode" in code
    assert "--ephemeral --seed" in code
