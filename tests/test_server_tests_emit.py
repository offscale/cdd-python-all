"""Test for server test generation."""

from openapi_client.tests.emit_server_tests import emit_server_tests
from openapi_client.models import OpenAPI, Components, Schema, PathItem, Operation


def test_emit_server_tests_empty():
    """Test emit_server_tests with empty spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    assert emit_server_tests(spec) == {}


def test_emit_server_tests_with_models():
    """Test emit_server_tests with models."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "User": Schema(type="object", properties={}),
            }
        ),
        paths={"/users": PathItem(get=Operation(operationId="get_users"))},
    )
    code = emit_server_tests(spec)

    assert "def test_db_config_ephemeral():" in code["test_unit.py"]
    assert "def test_dao_factory_stub():" in code["test_unit.py"]
    assert "def test_dao_factory_concrete():" in code["test_unit.py"]
    assert "def test_seeder_referential_integrity():" in code["test_unit.py"]
    assert "test_stub.py" in code
    assert "client.get('/users')" in code["test_stub.py"]
    assert (
        "def test_ephemeral_clean_state(ephemeral_client):" in code["test_ephemeral.py"]
    )
    assert "def test_seeded_state(seeded_client):" in code["test_seeded.py"]
    assert "def test_cors_preflight():" in code["test_advanced.py"]
    assert "def test_strict_validation_mock():" in code["test_advanced.py"]
    assert "def test_auth_enforcement_mock():" in code["test_advanced.py"]
    assert "def test_trigger_webhook():" in code["test_advanced.py"]
    assert "def test_auth_endpoints_mock():" in code["test_advanced.py"]


def test_emit_server_tests_no_paths():
    """Test emit_server_tests with models but no paths."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "User": Schema(type="object", properties={}),
            }
        ),
    )
    code = emit_server_tests(spec)

    assert "test_stub.py" in code
    assert "pass # No GET endpoints found in spec" in code["test_stub.py"]
